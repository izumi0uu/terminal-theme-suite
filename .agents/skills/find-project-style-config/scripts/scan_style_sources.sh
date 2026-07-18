#!/usr/bin/env bash
set -euo pipefail

ROOT=${1:-.}
TARGET_PATTERN=${2:-}

if [[ ! -d "$ROOT" ]]; then
  echo "error: project root is not a directory: $ROOT" >&2
  exit 2
fi

if ! command -v rg >/dev/null 2>&1; then
  echo "error: ripgrep (rg) is required" >&2
  exit 2
fi

cd "$ROOT"

EXCLUDES=(
  --glob '!node_modules/**'
  --glob '!dist/**'
  --glob '!build/**'
  --glob '!.next/**'
  --glob '!coverage/**'
  --glob '!vendor/**'
  --glob '!target/**'
  --glob '!.git/**'
)

section() {
  printf '\n## %s\n' "$1"
}

section "Repository rules and build manifests"
rg --files "${EXCLUDES[@]}" \
  --glob 'AGENTS.md' \
  --glob '.cursorrules' \
  --glob 'package.json' \
  --glob 'pnpm-workspace.yaml' \
  --glob 'vite.config.*' \
  --glob 'next.config.*' \
  --glob 'astro.config.*' \
  --glob 'svelte.config.*' \
  --glob 'nuxt.config.*' \
  --glob 'tailwind.config.*' \
  --glob 'components.json' \
  --glob 'Cargo.toml' \
  --glob 'pyproject.toml' \
  --glob 'requirements*.txt' \
  --glob 'go.mod' \
  --glob '*.xcodeproj/project.pbxproj' \
  | sort | sed -n '1,160p' || true

section "Style-stack dependency signals"
rg -n -i "${EXCLUDES[@]}" \
  --glob 'package.json' \
  --glob 'pnpm-lock.yaml' \
  --glob 'yarn.lock' \
  --glob 'package-lock.json' \
  --glob 'pyproject.toml' \
  --glob 'requirements*.txt' \
  --glob 'Cargo.toml' \
  'tailwind|@mui|material-ui|shadcn|radix|chakra|mantine|styled-components|emotion|sass|less|vanilla-extract|styled-system|ink|textual|rich|ratatui|tui|herdr|oh-my-pi|iterm' \
  | sed -n '1,220p' || true

section "Likely tokens, themes, global styles, and framework adapters"
rg --files "${EXCLUDES[@]}" \
  | rg -i '(^|/)(styles?|theme|themes|tokens?|design-system|palette|colors?|providers?)(/|\.|$)|globals?\.(css|scss|sass|less)$|app\.(css|scss|sass|less)$|index\.(css|scss|sass|less)$|components\.json$|tailwind\.config\.|postcss\.config\.' \
  | sed -n '1,260p' || true

section "Definition, provider, import, and runtime consumption signals"
rg -n -i "${EXCLUDES[@]}" \
  --glob '*.{ts,tsx,js,jsx,vue,svelte,astro,css,scss,sass,less,html,py,rs,toml,json,yaml,yml}' \
  'ThemeProvider|CssVarsProvider|createTheme|extendTheme|MantineProvider|ChakraProvider|ConfigProvider|build_theme|apply_theme|load_config|theme_profile|@theme|@import|import .*\.(css|scss|sass|less)|var\(--|data-theme|color-scheme|prefers-color-scheme|class(Name)?=.*dark|attachShadow|shadowRoot|adoptedStyleSheets|setProperty\(' \
  | sed -n '1,320p' || true

section "Cascade, scope, and override signals"
rg -n -i "${EXCLUDES[@]}" \
  --glob '*.{css,scss,sass,less,ts,tsx,js,jsx,vue,svelte,astro,html}' \
  '@layer|!important|:root|:host|::part|::theme|shadowRoot|adoptedStyleSheets|style\.setProperty|documentElement\.(classList|dataset)|localStorage.*theme|matchMedia\(' \
  | sed -n '1,280p' || true

section "Generated or third-party candidates (do not edit without proof)"
rg --files --hidden --no-ignore \
  --glob 'dist/**' \
  --glob 'build/**' \
  --glob '.next/**' \
  --glob 'coverage/**' \
  --glob 'vendor/**' \
  --glob '*.min.css' \
  --glob '*.min.js' \
  | sed -n '1,160p' || true

if [[ -n "$TARGET_PATTERN" ]]; then
  section "Target-specific references: $TARGET_PATTERN"
  rg -n -i "${EXCLUDES[@]}" -- "$TARGET_PATTERN" | sed -n '1,260p' || true
fi
