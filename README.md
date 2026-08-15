# Terminal Theme Suite

Switch an iTerm2 color profile, wallpaper, [Oh My Pi](https://github.com/can1357/oh-my-pi)
theme, [Herdr](https://github.com/ogulcancelik/herdr) theme, Claude Code theme,
Codex CLI syntax theme, and Hermes CLI skin as one coordinated suite.

The same command powers both the CLI and iTerm2 shortcuts, so switching works even
while OMP, Herdr, Vim, or another full-screen terminal program has focus.

## Features

- Coordinated semantic palettes for iTerm2, OMP, Herdr, Claude Code, Codex CLI, and Hermes CLI
- 37 curated self-contained presets with bundled PNG wallpapers
- Private custom wallpaper overrides that are never added to this repository
- iTerm2 Dynamic Profiles that inherit your font, shell, and window settings
- `Control+Option+T` for next theme
- `Control+Option+Shift+T` for previous theme
- New tabs and windows inherit the active suite through `Command+T` and `Command+N`
- Interactive `fzf` picker and scriptable commands
- Atomic configuration writes and Herdr validation before live reload
- An OMP startup extension that enables live reload in every new OMP process
- Native Claude Code custom theme with hot reload after one-time activation
- Native Codex `.tmTheme` generation for syntax highlighting and file diffs
- Native Hermes skin generation for both the classic CLI and modern TUI
- Parallel application updates with an inter-process switch lock

There are 37 built-in suites; the complete wallpaper catalog is below.

| Hero Amber | Catppuccin Mocha | Tokyo Night | Dracula |
| --- | --- | --- | --- |
| ![Hero Amber wallpaper](src/terminal_theme_suite/data/presets/hero-amber/wallpaper.png) | ![Catppuccin wallpaper](src/terminal_theme_suite/data/presets/catppuccin/wallpaper.png) | ![Tokyo Night wallpaper](src/terminal_theme_suite/data/presets/tokyo-night/wallpaper.png) | ![Dracula wallpaper](src/terminal_theme_suite/data/presets/dracula/wallpaper.png) |

## Wallpaper catalog

<table>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/android18-neon/wallpaper.png" width="320" loading="lazy" alt="Android 18 Neon wallpaper"><br><b>Android 18 Neon</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/android18-redline/wallpaper.png" width="320" loading="lazy" alt="Android 18 Redline wallpaper"><br><b>Android 18 Redline</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/apex-cloudline/wallpaper.png" width="320" loading="lazy" alt="Apex Cloudline wallpaper"><br><b>Apex Cloudline</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/blonde-charcoal/wallpaper.png" width="320" loading="lazy" alt="Blonde Charcoal wallpaper"><br><b>Blonde Charcoal</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/blonde-peek-gold/wallpaper.png" width="320" loading="lazy" alt="Blonde Peek Gold wallpaper"><br><b>Blonde Peek Gold</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/bluehair-night-city/wallpaper.png" width="320" loading="lazy" alt="Bluehair Night City wallpaper"><br><b>Bluehair Night City</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/capsule-city/wallpaper.png" width="320" loading="lazy" alt="Capsule City wallpaper"><br><b>Capsule City</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/catppuccin/wallpaper.png" width="320" loading="lazy" alt="Catppuccin Mocha wallpaper"><br><b>Catppuccin Mocha</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/dracula/wallpaper.png" width="320" loading="lazy" alt="Dracula wallpaper"><br><b>Dracula</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/dragon-ball-lineart/wallpaper.png" width="320" loading="lazy" alt="Dragon Ball Lineart wallpaper"><br><b>Dragon Ball Lineart</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/duckegg-fashion/wallpaper.png" width="320" loading="lazy" alt="Duckegg Fashion wallpaper"><br><b>Duckegg Fashion</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/fern-lilac/wallpaper.png" width="320" loading="lazy" alt="Fern Lilac wallpaper"><br><b>Fern Lilac</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/graffiti-bubble/wallpaper.png" width="320" loading="lazy" alt="Graffiti Bubble wallpaper"><br><b>Graffiti Bubble</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/hazel-tangerine/wallpaper.png" width="320" loading="lazy" alt="Hazel Tangerine wallpaper"><br><b>Hazel Tangerine</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/hero-amber/wallpaper.png" width="320" loading="lazy" alt="Hero Amber wallpaper"><br><b>Hero Amber</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/lavender-elf-dawn/wallpaper.png" width="320" loading="lazy" alt="Lavender Elf Dawn wallpaper"><br><b>Lavender Elf Dawn</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/lucy-night-balcony/wallpaper.png" width="320" loading="lazy" alt="Lucy Night Balcony wallpaper"><br><b>Lucy Night Balcony</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/maid-raspberry/wallpaper.png" width="320" loading="lazy" alt="Maid Raspberry wallpaper"><br><b>Maid Raspberry</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/orbital-heroine/wallpaper.png" width="320" loading="lazy" alt="Orbital Heroine wallpaper"><br><b>Orbital Heroine</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/pink-braids-noir/wallpaper.png" width="320" loading="lazy" alt="Pink Braids Noir wallpaper"><br><b>Pink Braids Noir</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/rooftop-blue-hour/wallpaper.png" width="320" loading="lazy" alt="Rooftop Blue Hour wallpaper"><br><b>Rooftop Blue Hour</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/rooftop-golden-hour/wallpaper.png" width="320" loading="lazy" alt="Rooftop Golden Hour wallpaper"><br><b>Rooftop Golden Hour</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/ruri-dragon/wallpaper.png" width="320" loading="lazy" alt="Ruri Dragon wallpaper"><br><b>Ruri Dragon</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/sailor-saturn-lavender/wallpaper.png" width="320" loading="lazy" alt="Sailor Saturn Lavender wallpaper"><br><b>Sailor Saturn Lavender</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/sailor-saturn-violet/wallpaper.png" width="320" loading="lazy" alt="Sailor Saturn Violet wallpaper"><br><b>Sailor Saturn Violet</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/saturn-girl-purple/wallpaper.png" width="320" loading="lazy" alt="Saturn Girl Purple wallpaper"><br><b>Saturn Girl Purple</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/showa-street/wallpaper.png" width="320" loading="lazy" alt="Showa Street wallpaper"><br><b>Showa Street</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/summer-cloud/wallpaper.png" width="320" loading="lazy" alt="Summer Cloud wallpaper"><br><b>Summer Cloud</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/toga-signal-yellow/wallpaper.png" width="320" loading="lazy" alt="Toga Signal Yellow wallpaper"><br><b>Toga Signal Yellow</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/tokyo-night/wallpaper.png" width="320" loading="lazy" alt="Tokyo Night wallpaper"><br><b>Tokyo Night</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/trunks-solar-yellow/wallpaper.png" width="320" loading="lazy" alt="Trunks Solar Yellow wallpaper"><br><b>Trunks Solar Yellow</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/vinyl-bed-chill/wallpaper.png" width="320" loading="lazy" alt="Vinyl Bed Chill wallpaper"><br><b>Vinyl Bed Chill</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/wake-up-editorial/wallpaper.png" width="320" loading="lazy" alt="Wake Up Editorial wallpaper"><br><b>Wake Up Editorial</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/warrior-sky-cliff/wallpaper.png" width="320" loading="lazy" alt="Warrior Sky Cliff wallpaper"><br><b>Warrior Sky Cliff</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/whitecap-blue/wallpaper.png" width="320" loading="lazy" alt="Whitecap Blue wallpaper"><br><b>Whitecap Blue</b></td><td align="center"><img src="src/terminal_theme_suite/data/presets/whitehair-redline/wallpaper.png" width="320" loading="lazy" alt="Whitehair Redline wallpaper"><br><b>Whitehair Redline</b></td></tr>
<tr><td align="center"><img src="src/terminal_theme_suite/data/presets/yellow-circuit/wallpaper.png" width="320" loading="lazy" alt="Yellow Circuit wallpaper"><br><b>Yellow Circuit</b></td></tr>
</table>

## Requirements

- macOS and iTerm2
- Python 3.9 or newer
- Git LFS
- OMP and Herdr are optional
- Claude Code 2.1.118 or newer is optional
- Codex CLI is optional
- Hermes Agent 0.18 or newer is optional
- `fzf` is optional but recommended for the interactive picker
- iTerm2's Python API, enabled automatically by `term-theme init`

## Install

```bash
git lfs install
git clone https://github.com/izumi0uu/terminal-theme-suite.git
cd terminal-theme-suite
git lfs pull
./scripts/install.sh
```

The installer creates an isolated virtual environment under
`~/.local/share/terminal-theme-suite` and links `term-theme` into `~/.local/bin`.
It also installs a small AutoLaunch daemon in iTerm2's standard Scripts directory.
During initialization it configures OMP's dark theme, light theme, Nerd Font symbol
preset, and live-reload extension once; normal theme switches do not run `omp config`.
Restart iTerm2 once after the first installation. iTerm2 may then ask to download its
official Python Runtime (about 169 MB); approve that one-time prompt. The Runtime is
maintained and verified by iTerm2, not this project. The daemon uses the API only to
change Profile settings in local sessions.

Run a health check:

```bash
term-theme doctor
```

## Usage

```bash
term-theme list
term-theme choose
term-theme use hero-amber
term-theme next
term-theme previous
term-theme current
term-theme use tokyo-night --timing
```

Running `term-theme` without arguments opens the picker in an interactive terminal,
or lists themes when output is redirected.

### Wallpapers

Every built-in suite includes a matching PNG wallpaper. The original four use
1586x992 assets; the 33 image-matched suites use 2880x1800 assets. No wallpaper setup
is required after installation. Custom images are copied into the private user
configuration directory by default and override only the selected suite:

```bash
term-theme background set hero-amber ~/Pictures/amber-terminal.png
term-theme background set tokyo-night ~/Pictures/tokyo-terminal.png
```

Use `--reference` to keep the image in its original location:

```bash
term-theme background set catppuccin ~/Pictures/catppuccin.png --reference
```

Supported formats are PNG, JPEG, HEIC, and WebP. iTerm2 renders the image; this
project does not upload, modify, or inspect it.

Disable a wallpaper or restore its bundled preset:

```bash
term-theme background clear dracula  # disable the image
term-theme background reset dracula  # restore the bundled wallpaper
```

## How It Works

One semantic palette generates all application-specific settings:

```text
theme suite
  -> iTerm2 Dynamic Profile: ANSI 0-15, foreground, cursor, selection, wallpaper
  -> OMP custom theme: messages, Markdown, tools, syntax, status line
  -> Herdr config: panels, text, borders, status colors, live reload
  -> Claude Code custom theme: prompts, diffs, messages, status, subagents
  -> Codex .tmTheme: fenced code syntax and inserted/removed diff scopes
  -> Hermes skin: prompts, banners, completions, status, selection, and feedback
```

The generated iTerm2 profiles use the current default profile as their parent. This
keeps existing fonts, shell integration, working-directory behavior, and window
preferences. The switcher also updates iTerm2's persistent default Profile GUID and
calls `async_make_default`, so standard `Command+T` and `Command+N` actions use the
active suite even while iTerm2 is already running.

iTerm2 shortcuts use the native `Run Coprocess` key action to invoke the same CLI as
manual commands. The CLI updates OMP and Herdr, then asks a small AutoLaunch daemon to
call `async_set_profile` for live sessions and `async_make_default` for new sessions.
The daemon keeps one trusted connection through iTerm2's own Python Runtime, avoiding
repeated API authorization and connection setup. Coprocess output never becomes text
inside OMP or Herdr.

OMP is configured to use `terminal-theme-suite` for both dark and light modes and
to use Nerd Font symbols during `term-theme init`. A small OMP extension selects the
managed theme through OMP's in-process API at startup. This enables OMP's
theme watcher, so later switches repaint every OMP process that loaded the extension.
Processes that were already running when the extension was first installed need one
restart; restarting iTerm2 alone is insufficient when Herdr keeps the OMP pane alive.
The extension publishes one per-process presence file under
`~/.config/terminal-theme-suite/omp-runtime/`, identified by PID, process start time,
and a random token. Each switch atomically writes `omp-generation.json`; the extension
reloads the theme and acknowledges that exact generation and theme hash. `doctor`,
`omp-live-reload status`, and theme-switch output therefore distinguish an installed
extension from a running watcher and a theme that was actually applied. There is no
periodic heartbeat or background write. Restarting is not required after later theme
switches.

The switch hot path only atomically replaces the managed OMP theme JSON; it does not
start the OMP CLI. All application adapters run concurrently after the target theme
is resolved. A file lock serializes overlapping shortcut presses, including
calculating `next` and `previous`, so overlapping switches cannot interleave. Run
`term-theme repair` if `term-theme doctor` reports OMP configuration drift.

Herdr's existing TOML configuration is preserved. Only `[theme]` and
`[theme.custom]` values are managed, followed by `herdr config check` and
`herdr server reload-config`.

Claude Code uses one stable managed theme at
`~/.claude/themes/terminal-theme-suite.json`. The adapter preserves unrelated
fields in `~/.claude/settings.json` and selects
`custom:terminal-theme-suite`. If the themes directory did not exist when a
Claude Code session started, restart that session once after the first switch.
Later switches rewrite the same active file and Claude Code hot-reloads it.
Claude does not expose an application ACK, so the switcher reports the documented
hot-reload behavior without claiming runtime confirmation.

Codex CLI uses one stable TextMate theme at
`~/.codex/themes/terminal-theme-suite.tmTheme`. The adapter preserves the full
`~/.codex/config.toml` document and sets `[tui] theme = "terminal-theme-suite"`.
Codex currently loads external `.tmTheme` data into process memory and does not
watch the file. After a suite switch, reselect `terminal-theme-suite` with `/theme`
or restart a running Codex TUI to refresh syntax and diff colors. The iTerm2 profile
continues to control the terminal background, ANSI palette, and overall foreground;
the `.tmTheme` does not recolor every Codex TUI element or the Codex desktop app.

Hermes uses one stable managed skin at
`~/.hermes/skins/terminal-theme-suite.yaml`. The adapter preserves unrelated
values in `~/.hermes/config.yaml` and sets
`display.skin: terminal-theme-suite`. Both the classic Hermes CLI and modern TUI
consume the same skin. Running Hermes sessions cache skin data; after an external
suite switch, run `/skin terminal-theme-suite` in that session or restart it.
The TUI emits its native `skin.changed` event when `/skin` is used, so the repaint
is immediate without restarting the underlying agent session.

## Configuration

User configuration:

```text
~/.config/terminal-theme-suite/config.json
```

Example override:

```json
{
  "base_profile_guid": null,
  "scope": "all",
  "shortcuts": true,
  "terminal_typography": {
    "mode": "inherit"
  },
  "themes": {
    "hero-amber": {
      "background": "~/.config/terminal-theme-suite/backgrounds/hero-amber.png",
      "blend": 0.65,
      "enabled": true
    },
    "dracula": {
      "background": false,
      "enabled": false
    }
  }
}
```

Set `scope` to `current` to switch only the focused iTerm2 session. The default is
`all` because OMP and Herdr use global theme configuration.

Terminal font family, size, spacing, ligatures, and bold/italic face availability are
global user settings shared by every terminal application. The default `inherit` mode
copies them from the current iTerm2 base profile. Use `managed` only when this project
should make the values explicit in every generated profile:

```json
{
  "terminal_typography": {
    "mode": "managed",
    "font_family": "MesloLGSNF-Regular",
    "non_ascii_font_family": "MesloLGSNF-Regular",
    "font_size": 14,
    "horizontal_spacing": 1,
    "vertical_spacing": 1.05,
    "ligatures": true,
    "use_bold_font": true,
    "use_italic_font": true
  }
}
```

Run `term-theme sync` after changing typography. OMP's `symbolPreset: nerd` selects
icons but does not install or select a Nerd Font.

Regenerate profiles after manual changes:

```bash
term-theme sync
```

## Preset Format

Each built-in suite is a self-contained directory under
`src/terminal_theme_suite/data/presets/<id>/`:

```text
hero-amber/
├── preset.json
└── wallpaper.png
```

`preset.json` is the authority for the semantic palette, 16 ANSI colors, wallpaper
settings, and target-specific overrides. Codex targets may additionally define
semantic `styles` using `bold`, `italic`, and `underline`; OMP, Claude Code, and Hermes
keep their application-managed emphasis. Wallpaper paths are relative to the preset
directory. The loader discovers directories automatically, so adding a preset does
not require changing Python code. IDs must be unique and match their directory names.
Optional `preview` and `license_file` fields can reference files in the same directory
without changing the loader or package layout.

The versioned schema lives at
`src/terminal_theme_suite/data/schemas/preset.schema.json`. Runtime loading validates
the same core invariants, including required semantic colors, image existence, safe
relative filenames, and Herdr/OMP target structure. CI validates every bundled preset
against the JSON Schema.

## Privacy and Safety

- Do not assume the repository license covers newly imported artwork. Presets omit
  source and license metadata until those rights are verified.
- Custom wallpapers and local paths stay under your home directory and are ignored
  by Git.
- The project does not use network APIs at runtime.
- Existing iTerm2 profiles are not rewritten.
- Existing Claude Code settings are preserved except for the selected `theme`.
- Existing Codex config, providers, MCP servers, plugins, and comments are preserved.
- Existing Hermes configuration values are preserved except for `display.skin`.
- Herdr config changes are validated and rolled back when validation fails.
- OMP model, provider, and authentication settings are not modified.
- The OMP extension only calls the local `ctx.ui.setTheme` API at session startup and
  when `term-theme` publishes a new generation.

## 中文快速说明

这个工具把 iTerm2 配色和背景图、OMP 主题、Herdr 主题、Claude Code 主题、Codex CLI 代码主题、Hermes CLI 皮肤作为一套配置同步切换。

```bash
term-theme list                  # 查看全部套装
term-theme                       # 使用 fzf 选择
term-theme use hero-amber        # 指定套装
term-theme next                  # 下一套
term-theme previous              # 上一套
term-theme use tokyo-night --timing # 显示各阶段耗时
term-theme background set hero-amber ~/Pictures/background.png
term-theme background clear hero-amber  # 关闭该套背景图
term-theme background reset hero-amber  # 恢复项目内置背景图
```

iTerm2 内快捷键：

- `Control+Option+T`：下一套
- `Control+Option+Shift+T`：上一套

安装或运行 `term-theme init` 后，之前已经运行的 OMP 需要重开一次以加载扩展。Herdr 会保留内部进程，所以只重启 iTerm2 不会重启 Herdr 里的 OMP。扩展加载后会在 `~/.config/terminal-theme-suite/omp-runtime/` 写一次运行状态；每次切换只在主题真正重载后写入对应 generation 和主题 hash 的 ACK，没有定时心跳。`doctor` 和 `omp-live-reload status` 只有在运行中的 OMP 真正加载扩展且最新主题已确认后才会报告 watcher active。

Claude Code 第一次接入时需要重启当前 Claude 会话一次；以后切换会重写同一个 `terminal-theme-suite.json`，由 Claude Code 自动热重载。普通切换中所有应用适配器会并行更新。多个快捷键命令会通过文件锁依次执行，避免多次切换彼此交错。`term-theme doctor` 如果提示 OMP 配置漂移，运行：

Codex CLI 会读取 `~/.codex/themes/terminal-theme-suite.tmTheme`，只负责代码高亮和 diff。Codex 目前不会监听外部主题文件，所以每次切换后，需要在正在运行的 Codex TUI 中用 `/theme` 重新选择 `terminal-theme-suite`，或者重启该 Codex 会话。

Hermes CLI 会读取 `~/.hermes/skins/terminal-theme-suite.yaml`。经典 CLI 和现代 TUI 共用这套皮肤；切换后在已运行的 Hermes 会话中执行 `/skin terminal-theme-suite` 即可立即刷新，或者重启该会话。

字体族、字号、间距和连字由 `terminal_typography` 统一管理。默认 `inherit` 保留 iTerm2 当前字体；设置为 `managed` 后运行 `term-theme sync`，四个 Coding Agent 会共享生成 Profile 的字体。只有 Codex 支持预设中的 `bold`、`italic`、`underline` 语义样式，OMP、Claude Code 和 Hermes 保留各自内置样式。

```bash
term-theme repair
```

如果需要单独检查或管理这个启动扩展：

```bash
term-theme omp-live-reload status
term-theme omp-live-reload install
term-theme omp-live-reload remove
```

## Development

Bundled preset wallpapers are stored with Git LFS. Install Git LFS with your package
manager, then materialize the image files after cloning:

```bash
git lfs install
git lfs pull
```

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

## License

MIT
