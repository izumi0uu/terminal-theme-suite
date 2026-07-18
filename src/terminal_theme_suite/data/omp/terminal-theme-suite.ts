import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { randomUUID } from "node:crypto";

const THEME_NAME = "terminal-theme-suite";
const GENERATION_FILE_NAME = "omp-generation.json";
const WATCH_DEBOUNCE_MS = 25;

type Generation = {
  generation: string;
  theme_sha256: string;
};

const runtimeToken = randomUUID();
const processStartedAt = new Date(
  Date.now() - process.uptime() * 1000,
).toISOString();
let runtimePath: string | undefined;
let generationPath: string | undefined;
let watcher: fs.FSWatcher | undefined;
let debounceTimer: ReturnType<typeof setTimeout> | undefined;
let reloadQueue = Promise.resolve();
let ready = false;
let appliedGeneration: string | null = null;
let appliedThemeSha256: string | null = null;
let appliedAt: string | null = null;
let error: string | null = null;
let errorGeneration: string | null = null;
let observedGenerationKey: string | null = null;

function configDirectory(): string {
  const configured = process.env.TTS_CONFIG_DIR;
  return configured
    ? path.resolve(configured)
    : path.join(os.homedir(), ".config", "terminal-theme-suite");
}

function readGeneration(): Generation | null {
  if (!generationPath) {
    return null;
  }
  try {
    const value = JSON.parse(fs.readFileSync(generationPath, "utf8"));
    if (
      typeof value.generation === "string" &&
      typeof value.theme_sha256 === "string"
    ) {
      return value as Generation;
    }
  } catch {
    // Atomic replacement may briefly leave no readable generation file.
  }
  return null;
}

function writeRuntimeState(): void {
  if (!runtimePath) {
    return;
  }
  try {
    const temporary = `${runtimePath}.${runtimeToken}.tmp`;
    fs.writeFileSync(
      temporary,
      `${JSON.stringify({
        pid: process.pid,
        theme: THEME_NAME,
        process_started_at: processStartedAt,
        token: runtimeToken,
        ready,
        applied_generation: appliedGeneration,
        applied_theme_sha256: appliedThemeSha256,
        applied_at: appliedAt,
        error,
        error_generation: errorGeneration,
      })}\n`,
      "utf8",
    );
    fs.renameSync(temporary, runtimePath);
  } catch {
    // Theme loading must not fail because runtime diagnostics are unavailable.
  }
}

async function reloadTheme(ctx: any, force = false): Promise<void> {
  const generation = readGeneration();
  const generationKey = generation
    ? `${generation.generation}:${generation.theme_sha256}`
    : "missing";
  if (!force && generationKey === observedGenerationKey) {
    return;
  }
  observedGenerationKey = generationKey;
  let result: any;
  try {
    result = await ctx.ui.setTheme(THEME_NAME);
  } catch (caught) {
    result = { success: false, error: String(caught) };
  }
  ready = result.success === true;
  if (ready) {
    appliedGeneration = generation?.generation ?? null;
    appliedThemeSha256 = generation?.theme_sha256 ?? null;
    appliedAt = new Date().toISOString();
    error = null;
    errorGeneration = null;
  } else {
    error = String(result.error ?? "theme activation failed");
    errorGeneration = generation?.generation ?? null;
  }
  writeRuntimeState();
  if (!result.success) {
    ctx.ui.notify(
      `Terminal Theme Suite could not load ${THEME_NAME}: ${error}`,
      "warning",
    );
  }
}

function scheduleReload(ctx: any): void {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }
  debounceTimer = setTimeout(() => {
    debounceTimer = undefined;
    reloadQueue = reloadQueue.then(() => reloadTheme(ctx)).catch(() => undefined);
  }, WATCH_DEBOUNCE_MS);
}

function removeOwnRuntimeState(): void {
  if (runtimePath) {
    try {
      const value = JSON.parse(fs.readFileSync(runtimePath, "utf8"));
      if (value.token === runtimeToken) {
        fs.unlinkSync(runtimePath);
      }
    } catch {
      // The runtime directory may already have been cleaned up.
    }
  }
}

function stopRuntime(): void {
  watcher?.close();
  watcher = undefined;
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = undefined;
  }
  removeOwnRuntimeState();
  runtimePath = undefined;
  generationPath = undefined;
}

export default function terminalThemeSuite(pi: any) {
  pi.on("session_start", async (_event: unknown, ctx: any) => {
    if (!ctx.hasUI) {
      return;
    }

    stopRuntime();
    const configRoot = configDirectory();
    const runtimeDirectory = path.join(configRoot, "omp-runtime");
    fs.mkdirSync(runtimeDirectory, { recursive: true });
    runtimePath = path.join(runtimeDirectory, `${process.pid}.json`);
    generationPath = path.join(configRoot, GENERATION_FILE_NAME);
    watcher = fs.watch(configRoot, () => {
      scheduleReload(ctx);
    });
    reloadQueue = reloadTheme(ctx, true);
    await reloadQueue;
  });

  pi.on("session_shutdown", async () => {
    stopRuntime();
  });
}
