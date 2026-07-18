---
name: derive-theme-from-image
description: Derive a readable, implementable semantic UI theme from one or more wallpapers, illustrations, photos, or screenshots. Use when Codex must inspect image composition and complexity, extract a raw palette, create a separate accessibility-adjusted palette, map semantic tokens to CSS, Tailwind, component frameworks, ANSI/iTerm2, Herdr, OMP, editor JSON, or TOML, verify WCAG contrast, preserve existing fonts/backgrounds/settings, or apply and screenshot-test the result after explicit authorization. Invoke find-project-style-config first only when the target configuration entry is unknown.
---

# Derive Theme From Image

Translate visual relationships from reference images into semantic interface roles. Do
not use the most frequent image colors directly as text, status, or selection colors.

## Permission Contract

- Analyze and recommend without writing when the user asks to inspect, derive, compare,
  explain, or propose a theme.
- Write only when the user explicitly asks to set, apply, update, install, or implement
  the theme.
- Before authorized writes, preserve unrelated configuration and create a targeted
  backup when changing user or application state.
- Preserve requested fonts, wallpaper paths, image modes, shell settings, providers,
  authentication, and unrelated preferences.
- Do not upload reference images or include private image paths in public artifacts.

## Inputs

Collect or infer:

- one or more reference images and each image's role;
- target application and target variant, such as dark, light, or both;
- known theme/config entry and output format;
- whether configuration changes are authorized;
- settings that must remain invariant.

If the target entry is unknown, invoke `$find-project-style-config` and use its handoff.
Do not invoke it when the authoritative configuration is already known.

## Workflow

### 1. Inspect image composition

View each image before extracting colors. Record dimensions, aspect ratio, subject
position, quiet regions, crop risk, brightness distribution, and visual complexity.

Use the read-only palette script for repeatable measurements:

```bash
uv run --no-project --with pillow \
  .agents/skills/derive-theme-from-image/scripts/extract_palette.py \
  /path/to/reference.png --colors 10
```

The script reports raw colors and regional edge complexity. It does not decide semantic
roles and never writes the image.

### 2. Keep two distinct palettes

Produce both:

1. **Image palette**: measured colors, coverage, brightness, and visual role.
2. **UI palette**: adjusted colors selected for semantic meaning and readability.

For every adjustment, state whether lightness, saturation, or hue changed and why. Keep
the image's relationships recognizable without treating fidelity as more important than
legibility.

### 3. Define semantic tokens

At minimum define:

```text
background  surface  text  text-muted  accent  border  selection
success     warning  error
```

Add target-specific roles only when consumed by the application. Use
[references/semantic-theme-mapping.md](references/semantic-theme-mapping.md) for the
detected target and its validation checklist.

### 4. Check contrast against actual surfaces

Test primary text, muted text, links/accents, borders or focus, selection pairs, and
status colors against every surface where they appear. Use the flat checker for a quick
single-surface measurement:

```bash
python .agents/skills/derive-theme-from-image/scripts/check_contrast.py \
  --background '#D09054' \
  --foreground '#120F0D' \
  --foreground '#0F355C'
```

Target at least `4.5:1` for normal text and `3:1` for large text or essential graphical
controls. Prefer `7:1` for persistent terminal body text when the image allows it.

For OMP or Herdr, audit the complete role-to-surface matrix instead of checking a few
representative colors:

```bash
uv run --no-project --with tomli \
  .agents/skills/derive-theme-from-image/scripts/audit_terminal_theme.py \
  --omp /path/to/generated-theme.json \
  --herdr /path/to/config.toml \
  --terminal-background '#D09054' \
  --min-score 85
```

Use the default weighted `85/100` gate unless the user or project defines another
threshold. A passing score means usable, not perfect. Always report every failed,
missing, invalid, unknown, or unresolved role and its likely effect. Add `--strict`
only for an explicitly requested release-grade audit.

Read
[references/omp-herdr-role-matrix.md](references/omp-herdr-role-matrix.md) when working
on OMP or Herdr. Treat
[references/terminal-role-matrix.json](references/terminal-role-matrix.json) as the
machine-readable classification authority.

### 5. Map to the real target structure

Map semantic roles through the authoritative adapter discovered in the project. For
terminal themes, include ANSI 0-15 plus foreground, background, cursor, link, selection,
and selected text. For image-backed themes, also verify blend, scale mode, and crop.

Do not emit unsupported keys. Validate against the target schema or configuration
checker before writing.

### 6. Sample wallpaper-backed surfaces

A flat background check is only an approximation when text renders over a wallpaper.
Simulate the real viewport, scale mode, crop anchor, and background blend:

```bash
uv run --no-project --with pillow \
  .agents/skills/derive-theme-from-image/scripts/sample_wallpaper_contrast.py \
  --image /path/to/wallpaper.png \
  --background '#D09054' \
  --blend 0.65 \
  --mode fill \
  --anchor bottom \
  --viewport 1200x800 \
  --viewport 700x900 \
  --foreground 'text=#120F0D:4.5' \
  --foreground 'muted=#2F2822:4.5' \
  --min-pass-coverage 90
```

Interpret `--blend 0` as image only and `--blend 1` as solid background only. Confirm
that semantic against the target application's actual implementation. Use the default
`90%` sampled-pixel coverage as a soft gate. Keep minimum, P1, P5, and worst-region
failures as warnings even when coverage passes; one extreme pixel must not fail the
theme. Use `--strict` only when every sampled pixel must pass.

### 7. Apply only with authorization

When authorized:

1. capture the current file/state and preserve a backup;
2. change only the authoritative tokens or documented adapter fields;
3. run formatter/schema/config validation;
4. reload through the application's supported mechanism;
5. verify current and newly created views when runtime defaults differ;
6. roll back if validation fails.

### 8. Screenshot and iterate

Capture the real target at representative dimensions. Inspect body text, muted labels,
links, syntax/code, status line, borders, selected state, focus, success/warning/error,
and image crop. Change one semantic relationship per iteration, then rerun contrast
checks. For OMP and Herdr, execute the representative state checklist in
[references/omp-herdr-role-matrix.md](references/omp-herdr-role-matrix.md). Do not
declare success from palette math alone.

## Output Format

Lead with the target and permission state, then report:

| Role | Image color | Final color | Contrast | Rationale |
| --- | --- | --- | --- | --- |
| Background | `#D09054` | `#D09054` | n/a | dominant quiet field |
| Text | `#040303` | `#120F0D` | `7.1:1` | softened black, AAA body text |
| Accent | `#2B7DC6` | `#0F355C` | `4.8:1` | darker blue for links/focus |

Also include:

- image composition and crop findings;
- semantic token set;
- target mapping path/format;
- weighted configuration score, selected threshold, and every failed role/surface pair;
- wallpaper coverage by viewport and role, including P5 and worst-region warnings;
- preserved settings;
- validation results;
- files changed and backup path, or `No files changed` for analysis-only work;
- screenshot findings and remaining risks.

## Relationship to Find Project Style Config

`$find-project-style-config` proves where values belong. This skill decides what the
values should be, maps them, and validates the rendered result. Never move palette
derivation into the discovery skill, and never guess a configuration entry here when
the first skill can prove it.
