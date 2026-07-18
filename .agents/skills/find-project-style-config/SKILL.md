---
name: find-project-style-config
description: Locate the authoritative source that controls colors, typography, spacing, dark mode, or other interface styling in an unfamiliar repository. Use when Codex must trace a target website, component, browser extension, desktop UI, terminal UI, iTerm2 profile, Herdr theme, or OMP theme from rendered output back through providers, adapters, imports, tokens, and build configuration; distinguish source-of-truth files from local overrides, generated assets, and third-party files; or identify the safest edit point before changing a theme. Default to read-only analysis.
---

# Find Project Style Config

Identify the smallest authoritative style source by proving its consumption chain. Do
not rank candidates only because their filenames contain `theme`, `style`, or `color`.

## Safety Contract

- Operate read-only unless the user explicitly asks to modify files.
- Treat requests to inspect, find, explain, diagnose, or recommend as read-only.
- Preserve existing worktree changes and report overlapping edits.
- Never edit generated bundles, caches, installed packages, or vendored files without
  proof that they are the intended source.
- Do not stop at a likely file. Trace it to the requested rendered target.

## Inputs

Establish these from the prompt and repository before searching:

- project root;
- target interface, route, window, component, or terminal application;
- desired change, such as colors, font, spacing, wallpaper, or dark mode;
- whether the user asked only for analysis or explicitly authorized edits.

If the target remains ambiguous but multiple candidates would lead to materially
different recommendations, ask one focused question. Otherwise proceed with the most
specific target supported by the repository.

## Workflow

### 1. Read project authority first

Read every applicable `AGENTS.md` from the repository root down to the target. Inspect
the build manifest, dependency manifest, workspace configuration, and relevant entry
points. Do not make changes during this step.

Run the read-only scanner when discovery is broad:

```bash
bash .agents/skills/find-project-style-config/scripts/scan_style_sources.sh \
  /path/to/project 'TargetComponent|target-route'
```

Treat scanner output as leads, not conclusions.

### 2. Infer the active style stack

Use dependencies, imports, providers, and build plugins to identify the active stack.
Check [references/ecosystem-style-map.md](references/ecosystem-style-map.md) only for
the detected ecosystem. Verify version-sensitive differences such as Tailwind v3
configuration versus Tailwind v4 CSS `@theme`.

### 3. Start at the rendered target and trace backward

Locate the target component or screen, then follow the chain in reverse:

```text
rendered target <- local classes/props <- provider or adapter <- semantic tokens <- authority
```

Also record the forward chain for the final report:

```text
definition -> framework mapping -> import/provider -> rendered target
```

Use concrete references: imported module names, provider props, CSS variables,
configuration keys, runtime profile names, or generated manifest entries.

### 4. Classify every relevant file

Assign candidates to exactly one primary class:

| Class | Meaning |
| --- | --- |
| Authoritative source | canonical semantic tokens or theme values for the target |
| Framework adapter | maps authority into Tailwind, MUI, shadcn, TUI, iTerm2, Herdr, or OMP |
| Local override | intentionally narrows or replaces values for a component or scope |
| Generated/third-party | build output, cache, dependency, installed bundle, or derived file |

A local override may be the safest entry only when the requested change is intentionally
local. State that tradeoff explicitly.

### 5. Prove precedence and runtime state

For CSS, check origin, `@layer`, importance, specificity, scope, and import order. Check
inline styles, CSS-in-JS insertion order, nested providers, Shadow DOM, `::part`, adopted
style sheets, and runtime calls to `style.setProperty`.

For non-web targets, check profile inheritance, dark/light slots, persisted user
preferences, startup extensions, generated profiles, environment variables, and live
reload behavior. A correct source file is not sufficient when runtime state replaces it.

### 6. Recommend the safest edit point

Choose the highest-level source that affects exactly the requested scope. Include:

- why it is authoritative;
- which adapters and consumers depend on it;
- which local overrides can still win;
- which files must not be edited;
- the smallest verification needed after a future change.

Do not edit merely because the best entry is known. Wait for an explicit change request.

## Chaining Contract

When `$derive-theme-from-image` needs a target mapping but the configuration entry is
unknown, run this skill first. Return a handoff containing:

- style stack and version;
- authoritative token/config path;
- adapter path;
- import/provider/render path;
- local overrides and runtime overrides;
- target format and validation command;
- files that must remain untouched.

Do not derive colors in this skill.

## Output Format

Report evidence in this order:

```text
Target: <interface or component>
Style stack: <framework/version and styling mechanism>
Authoritative source: <path and relevant symbol/selector/key>
Framework adapter: <path and mapping>
Consumption chain: <definition -> adapter -> provider/import -> render>
Local overrides: <paths or none>
Runtime/cascade overrides: <findings or none>
Do not modify: <generated/vendor paths>
Safest edit point: <path and reason>
Verification: <focused command or rendered check>
```

Use file and line references for every material claim.
