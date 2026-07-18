# Semantic Theme Mapping

Use the image palette as evidence, not as a finished UI palette. Preserve the visual
relationship while changing lightness, saturation, or hue enough to make interface
roles readable.

## Core Roles

| Token | Purpose | Selection guidance |
| --- | --- | --- |
| `background` | main canvas behind most content | choose a stable low-detail tone or an overlay compatible with the image |
| `surface` | panels, menus, toolbars | separate from background without competing with text |
| `text` | primary body and commands | target WCAG AA, preferably AAA for persistent terminal text |
| `text-muted` | secondary labels and metadata | remain distinguishable; do not use low opacity as the only strategy |
| `accent` | links, focus, active controls | preserve image identity while meeting contrast on its actual surface |
| `border` | dividers and component boundaries | visible at normal brightness without becoming a second text color |
| `selection` | selected text/background | check both selected background and selected foreground together |
| `success` | positive status | distinguish from warning/error without relying only on hue |
| `warning` | caution and pending state | usually needs lightness correction on warm images |
| `error` | destructive/error state | verify text, icon, and filled-state variants separately |

## Contrast Targets

- Normal text: WCAG AA `4.5:1`; AAA `7:1` when practical.
- Large text and essential graphical controls: AA `3:1`.
- Muted text still needs `4.5:1` when it conveys required information.
- Focus indicators and adjacent control boundaries should reach `3:1`.
- ANSI colors must be tested against the terminal background in both normal and bright
  forms; a hue being recognizable is not enough.

A flat foreground/background ratio is insufficient when text appears over a wallpaper
or when one role is reused across multiple containers. For OMP and Herdr, use the full
role and screenshot coverage in [omp-herdr-role-matrix.md](omp-herdr-role-matrix.md),
then sample the rendered wallpaper after scale, crop, anchor, and blend. Judge the
wallpaper with a configurable pixel-coverage gate while retaining minimum and
low-percentile failures as warnings.

## Image-Aware Adjustments

1. Record the raw color and its coverage before changing it.
2. Prefer quiet image regions for dense text; otherwise introduce a stable overlay or
   surface rather than forcing every foreground to compensate.
3. Preserve hue identity first, then adjust lightness, then reduce saturation if bright
   colors vibrate against the background.
4. Test the actual crop and scale mode. Subject placement can move behind terminal text
   when a landscape image is shown in a narrow window.
5. For light wallpapers, darken text and status colors; for dark wallpapers, lift them.
   Do not invert all colors mechanically.

## Target Mappings

### CSS and design tokens

Map core roles to variables such as `--background`, `--surface`, `--foreground`,
`--muted-foreground`, `--primary`, `--border`, and `--selection`. Confirm the project
adapter maps these variables into framework tokens before editing them.

### ANSI terminals and iTerm2

- ANSI 0/8: black and bright black; use them for neutral/dim roles.
- ANSI 1/9, 2/10, 3/11: error, success, warning families.
- ANSI 4/12, 5/13, 6/14: blue, magenta, cyan accents.
- ANSI 7/15: normal and bright text.
- Also map foreground, background, bold, cursor, cursor text, selection, selected text,
  link, wallpaper path, image mode, and blend.

Check profile inheritance and both current-session and new-session behavior.

### Herdr TOML

Map panels and primary background separately. Preserve unrelated terminal and key
settings. Validate `[theme]` plus `[theme.custom]`, then reload and inspect panels,
status colors, borders, selected rows, and transparent/reset surfaces.

### OMP JSON

Map model output, user text, tool output, Markdown, status line, borders, pending,
success, warning, and error roles. Preserve the supported schema exactly, configure
both dark and light theme slots when the application does not expose an automatic
variant, and verify the running process actually reloads the file.

### Editors

Map editor background/foreground, selection, line highlight, cursor, gutter, syntax
families, diagnostics, links, diff colors, and terminal ANSI values. Workbench chrome
and editor text often use separate token namespaces.

## Validation Pass

Capture the real application at representative sizes. Check body text, muted labels,
links, code/syntax, selected text, focus, status line, success/warning/error, panels,
and image crop. Change one semantic relationship at a time and rerun contrast checks
after each adjustment.
