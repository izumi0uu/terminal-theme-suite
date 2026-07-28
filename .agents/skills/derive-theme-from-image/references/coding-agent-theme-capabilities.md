# Coding Agent Theme Capabilities

Use this reference when a target includes OMP, Claude Code, Codex CLI, or Hermes CLI.
Treat the shared semantic palette as the authority, then emit only fields accepted by
each target.

## Capability Matrix

| Target | Semantic colors | Semantic font styles | Font family and size | Runtime refresh |
| --- | --- | --- | --- | --- |
| OMP | supported | application-managed | terminal-managed | file watcher with generation ACK |
| Claude Code | supported | application-managed | terminal-managed | stable custom theme file; restart once when first installed |
| Codex CLI | supported for syntax and diffs | `bold`, `italic`, `underline` on TextMate scopes | terminal-managed | reselect with `/theme` or restart |
| Hermes CLI | supported through skin colors | application-managed | terminal-managed | run `/skin <name>` or restart |

`application-managed` means the application uses emphasis internally but its public
theme format does not expose a supported setting for changing that emphasis. Do not
invent keys for it.

## Terminal Typography

Treat the terminal renderer as the authority for font family, non-ASCII font, size,
spacing, ligatures, and availability of bold or italic faces. Preserve these values by
default. Change them only when the user explicitly requests typography changes and the
terminal adapter has a documented managed mode.

Do not infer a font family from wallpaper colors or composition. An image may support a
recommendation such as high-density or low-contrast typography, but it does not prove a
font is installed or appropriate for terminal cell metrics.

OMP's Nerd Font symbol preset selects glyph names; it does not install or select the
terminal font. Verify the terminal font separately when icon coverage matters.

## Target Rules

### OMP

Map semantic colors into messages, Markdown, syntax, tools, thinking levels, status,
and diff roles. Preserve renderer-controlled emphasis. Validate the generated JSON
against the OMP theme schema and confirm the running generation ACK.

### Claude Code

Map semantic colors into the supported custom-theme override tokens. Preserve
Claude-controlled emphasis and the terminal font. Do not emit TextMate `fontStyle` or
terminal typography fields in the Claude theme JSON.

### Codex CLI

Map semantic colors into TextMate scopes for syntax and diffs. When the project or user
provides semantic styles, map only `bold`, `italic`, and `underline` into `fontStyle`.
Allow an empty style list to clear a default. Do not claim these scopes recolor Codex
workbench chrome or the desktop app.

### Hermes CLI

Map semantic colors into documented skin color roles. Preserve Hermes-controlled
bold/italic rules, branding, spinner data, and terminal typography unless the user asks
to change a supported field. Refresh a running session through its native `/skin`
command.

## Reporting

Report three separate groups:

1. **Derived**: semantic colors, surface relationships, contrast corrections, and any
   supported Codex scope styles.
2. **Preserved**: font family, font size, spacing, ligatures, shell settings, and
   application-managed emphasis.
3. **Unsupported or application-managed**: requested fields that the target cannot
   consume, including semantic font styles for OMP, Claude Code, and Hermes CLI.

Never present a skipped field as successfully applied.
