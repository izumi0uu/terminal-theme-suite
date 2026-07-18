# OMP and Herdr Role Matrix

The machine-readable authority is `terminal-role-matrix.json`. Update that file when a
target schema adds, removes, or changes a role. The auditor reports and penalizes unknown
and missing roles so schema drift cannot silently bypass validation; strict mode rejects
all structural warnings.

## Contents

- [Thresholds](#thresholds)
- [OMP coverage](#omp-coverage)
- [Herdr coverage](#herdr-coverage)
- [Wallpaper-backed surfaces](#wallpaper-backed-surfaces)
- [Screenshot scenarios](#screenshot-scenarios)
- [Completion gate](#completion-gate)

## Thresholds

| Content | Target | Default weight |
| --- | --- | --- |
| core body, selected, user, custom, and tool text | `4.5:1` | `3` |
| Markdown, syntax, diff, status, and status accents | `4.5:1` | `2` |
| secondary accents | `4.5:1` | `1.5` |
| borders, separators, focus, essential graphics | `3:1` | `1` |
| persistent terminal body text | prefer `7:1` | reported bonus target |

Compute a weighted pass score across every role/surface pair. The default soft gate is
`85/100`; allow callers to select another threshold. Keep every failed pair in the risk
report even when the overall score passes. Use strict `100/100` only when explicitly
requested or when a release policy requires it.

## OMP Coverage

The current matrix classifies all 66 `colors` keys and all three exported surfaces.

| Surface | Source |
| --- | --- |
| page | `export.pageBg` |
| card | `export.cardBg` |
| info | `export.infoBg` |
| selection | `colors.selectedBg` |
| user message | `colors.userMessageBg` |
| custom message | `colors.customMessageBg` |
| tool pending/success/error | their corresponding `*Bg` fields |
| status line | `colors.statusLineBg` |

Rules cover global text/status/accent roles, borders, selection text, user and custom
messages, every tool state, Markdown, code-block borders, diffs, all syntax roles,
thinking levels, bash/Python modes, and all status-line labels and separators.

Several OMP roles can render in more than one container. The matrix deliberately tests
them against every plausible page/card/info or tool-state surface. This is stricter than
checking each foreground against only the main page background.

## Herdr Coverage

The current matrix classifies all 16 `[theme.custom]` fields:

- surfaces: `panel_bg`, `surface0`, `surface1`, `surface_dim`;
- body text: `text`, `subtext0`;
- overlays and boundaries: `overlay0`, `overlay1`;
- accent/status text: `mauve`, `green`, `yellow`, `red`, `blue`, `teal`, `peach`,
  `accent`.

Body and accent text are checked against every Herdr surface. Overlays use the graphical
threshold against every surface.

## Wallpaper-Backed Surfaces

`panel_bg = "reset"` is not a color. Pass `--terminal-background` to the configuration
auditor for a flat approximation, then run the wallpaper sampler for the real result.

The sampler models:

```text
wallpaper -> scale/crop/anchor -> blend with terminal background -> rendered pixels
```

Its `--blend` value means the fraction of solid terminal background mixed over the
wallpaper: `0` shows the image, `1` shows only the solid background. Confirm this
assumption with an application screenshot because target versions can name or implement
blend controls differently.

Use representative wide, tall, and compact viewports. Match the actual fill/fit/stretch
mode and image anchor. Report minimum, first percentile, fifth percentile, median, pass
coverage, and the worst 3x3 region. The default wallpaper soft gate passes when at least
`90%` of sampled pixels meet the role threshold; a few extreme pixels remain warnings.

## Screenshot Scenarios

Capture all relevant states before declaring an OMP/Herdr theme complete.

OMP:

1. Normal conversation with primary, muted, thinking, user, and custom messages.
2. Tool pending, success, and error with title and multiline output.
3. Markdown heading, link, URL, quote, list, inline code, and fenced code.
4. Syntax sample containing every configured syntax family.
5. Added, removed, and context diff lines.
6. Status line with clean, dirty, staged, untracked, cost, output, and subagent states.

Herdr:

1. Main panel over the real terminal background or wallpaper.
2. Surface0/surface1/surface-dim panels with primary and secondary text.
3. Selected and unselected rows, overlays, borders, and focus.
4. Success, warning, error, accent, blue, teal, and peach states.
5. Narrow and wide layouts to expose different wallpaper regions.

## Completion Gate

Use a soft gate by default:

- configuration audit weighted score meets the selected threshold, default `85/100`;
- wallpaper sampled-pixel pass coverage meets the selected threshold, default `90%`;
- config/schema validators and live reload succeed;
- representative screenshots were inspected.

Unknown roles, missing roles, unresolved surfaces, low-contrast pairs, fifth-percentile
failures, and screenshot concerns remain visible warnings. Report the exact role, surface,
measured ratio, and likely visual effect. A passing score means usable, not perfect.

Use `--strict` to require `100/100`, zero structural warnings, and no failed sampled
pixels. Reserve strict mode for explicit requests and release audits.
