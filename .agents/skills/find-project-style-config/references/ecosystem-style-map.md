# Ecosystem Style Map

Use this map only after dependency and import evidence identifies the stack. Treat
paths as common patterns, not proof.

| Stack | Likely authority | Adapter or consumer | Runtime/cascade traps |
| --- | --- | --- | --- |
| Tailwind v3 | `tailwind.config.*`, global CSS variables | `content`, `theme.extend`, utility classes | preset/plugin order, JIT content omissions, local arbitrary values |
| Tailwind v4 | CSS `@theme`, `@import "tailwindcss"` | generated utilities and component classes | CSS import order, compatibility config, `@layer` order |
| shadcn/ui | global CSS semantic variables | `components.json`, Tailwind mappings, component variants | copied components are local source; variant classes may override tokens |
| MUI | `createTheme`/`extendTheme` object | `ThemeProvider`, `CssVarsProvider`, `sx`, component overrides | nested providers, color schemes, Emotion injection order |
| Chakra UI | theme/recipe configuration | `ChakraProvider`, semantic tokens, recipes | provider value, color-mode storage, component recipe precedence |
| Mantine | theme object and CSS variables resolver | `MantineProvider`, component styles API | nested providers and runtime color-scheme state |
| Ant Design | token algorithm/config | `ConfigProvider`, CSS-in-JS component tokens | static methods outside provider, hashed styles, algorithm overrides |
| Emotion/styled-components | theme object or CSS variables | provider plus styled consumers | multiple providers, insertion point, interpolated runtime props |
| CSS variables | `:root`, theme selector, token stylesheet | global import, component `var()` usage | later imports, selector specificity, fallback values, inline properties |
| CSS Modules | shared tokens plus module-local rules | component imports | hashed classes are generated; composition and import order still matter |
| Sass/Less | variables, maps, mixins, entry stylesheet | compiled imports | build-time values differ from runtime variables; generated CSS is not authority |
| Web Components | component stylesheet and exposed custom properties | shadow root, `:host`, `::part` | document CSS cannot cross a closed shadow root; inline adopted sheets win |
| Browser extension | shared tokens plus content/popup entry CSS | manifest entry, content script, shadow-root injection | host-page CSS, isolated worlds, multiple bundles, Shadow DOM |
| Electron | renderer theme source | preload/IPC state, renderer entry | OS theme events and persisted runtime preferences can override source defaults |
| Ink/React TUI | theme object/context | component props and terminal color library | terminal capability, `NO_COLOR`, direct component color props |
| Textual/Rich | TCSS/theme definitions | app `CSS_PATH`, widget classes | rule specificity, app variables, terminal true-color support |
| Ratatui | palette/style constructors | widget render calls | direct per-widget styles often bypass shared palette helpers |
| iTerm2 | profile plist or Dynamic Profile | session profile and preferences default GUID | live session properties, parent profile inheritance, light/dark slots |
| Herdr | `[theme]` and `[theme.custom]` TOML | server reload and panel rendering | built-in theme name may override custom fields; panel reset/transparency |
| OMP | selected theme JSON and config keys | startup extension/theme watcher | dark/light slots, runtime watcher, schema version, direct status colors |

## Authority Tests

Prefer a candidate only when evidence answers all of these:

1. A rendered target consumes the value directly or through a traceable adapter.
2. The file is source-controlled and participates in the active build/runtime path.
3. A later provider, import, inline style, runtime preference, or host environment does
   not replace the value.
4. Editing it affects the intended scope without broad unrelated changes.

## Generated and Vendor Signals

Treat `dist`, `build`, `.next`, hashed asset names, minified files, lockfiles,
`node_modules`, vendored sources, caches, and installed application bundles as
non-authoritative until the build or runtime proves otherwise. Trace their source map,
manifest entry, generator, or package configuration back to editable source.

## Cascade Checklist

For CSS targets, record origin, layer, importance, specificity, scope, and source order.
Also check inline styles, CSS-in-JS insertion points, nested providers, adopted style
sheets, shadow roots, and JavaScript calls to `style.setProperty` or theme state loaded
from storage.
