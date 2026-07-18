const THEME_NAME = "terminal-theme-suite";

export default function terminalThemeSuite(pi: any) {
  pi.on("session_start", async (_event: unknown, ctx: any) => {
    if (!ctx.hasUI) {
      return;
    }

    const result = await ctx.ui.setTheme(THEME_NAME);
    if (!result.success) {
      ctx.ui.notify(
        `Terminal Theme Suite could not load ${THEME_NAME}: ${result.error}`,
        "warning",
      );
    }
  });
}
