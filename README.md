# Terminal Theme Suite

Switch an iTerm2 color profile, wallpaper, [Oh My Pi](https://github.com/can1357/oh-my-pi)
theme, and [Herdr](https://github.com/ogulcancelik/herdr) theme as one coordinated suite.

The same command powers both the CLI and iTerm2 shortcuts, so switching works even
while OMP, Herdr, Vim, or another full-screen terminal program has focus.

## Features

- Coordinated semantic palettes for iTerm2, OMP, and Herdr
- Four original bundled wallpapers that work immediately after installation
- Private custom wallpaper overrides that are never added to this repository
- iTerm2 Dynamic Profiles that inherit your font, shell, and window settings
- `Control+Option+T` for next theme
- `Control+Option+Shift+T` for previous theme
- New tabs and windows inherit the active suite through `Command+T` and `Command+N`
- Interactive `fzf` picker and scriptable commands
- Atomic configuration writes and Herdr validation before live reload
- One fixed OMP custom-theme file, enabling live reload after the first OMP restart

Built-in suites:

- Hero Amber
- Catppuccin Mocha
- Tokyo Night
- Dracula

| Hero Amber | Catppuccin Mocha | Tokyo Night | Dracula |
| --- | --- | --- | --- |
| ![Hero Amber wallpaper](src/terminal_theme_suite/data/backgrounds/hero-amber.png) | ![Catppuccin wallpaper](src/terminal_theme_suite/data/backgrounds/catppuccin.png) | ![Tokyo Night wallpaper](src/terminal_theme_suite/data/backgrounds/tokyo-night.png) | ![Dracula wallpaper](src/terminal_theme_suite/data/backgrounds/dracula.png) |

## Requirements

- macOS and iTerm2
- Python 3.9 or newer
- OMP and Herdr are optional; missing integrations are skipped
- `fzf` is optional but recommended for the interactive picker
- iTerm2's Python API, enabled automatically by `term-theme init`

## Install

```bash
git clone https://github.com/izumi0uu/terminal-theme-suite.git
cd terminal-theme-suite
./scripts/install.sh
```

The installer creates an isolated virtual environment under
`~/.local/share/terminal-theme-suite` and links `term-theme` into `~/.local/bin`.
It also installs a small AutoLaunch daemon in iTerm2's standard Scripts directory.
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
```

Running `term-theme` without arguments opens the picker in an interactive terminal,
or lists themes when output is redirected.

### Wallpapers

Every built-in suite includes a matching 1920x1200 wallpaper. No wallpaper setup is
required after installation. Custom images are copied into the private user
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
term-theme background reset dracula  # restore dracula.png
```

## How It Works

One semantic palette generates all application-specific settings:

```text
theme suite
  -> iTerm2 Dynamic Profile: ANSI 0-15, foreground, cursor, selection, wallpaper
  -> OMP custom theme: messages, Markdown, tools, syntax, status line
  -> Herdr config: panels, text, borders, status colors, live reload
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
to use Nerd Font symbols. Restart every already-running OMP process once after the
initial setup. Later switches update the watched theme file and repaint live.

Herdr's existing TOML configuration is preserved. Only `[theme]` and
`[theme.custom]` values are managed, followed by `herdr config check` and
`herdr server reload-config`.

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

Regenerate profiles after manual changes:

```bash
term-theme sync
```

## Privacy and Safety

- Bundled wallpapers are original project assets distributed under this repository's
  license. Their editable SVG sources live in `artwork/wallpapers`.
- Custom wallpapers and local paths stay under your home directory and are ignored
  by Git.
- The project does not use network APIs at runtime.
- Existing iTerm2 profiles are not rewritten.
- Herdr config changes are validated and rolled back when validation fails.
- OMP model, provider, and authentication settings are not modified.

## 中文快速说明

这个工具把 iTerm2 配色和背景图、OMP 主题、Herdr 主题作为一套配置同步切换。

```bash
term-theme list                  # 查看全部套装
term-theme                       # 使用 fzf 选择
term-theme use hero-amber        # 指定套装
term-theme next                  # 下一套
term-theme previous              # 上一套
term-theme background set hero-amber ~/Pictures/background.png
term-theme background clear hero-amber  # 关闭该套背景图
term-theme background reset hero-amber  # 恢复项目内置背景图
```

iTerm2 内快捷键：

- `Control+Option+T`：下一套
- `Control+Option+Shift+T`：上一套

首次安装后，已经运行的 OMP 需要重开一次。此后 OMP 会监听活动主题文件，切换时可自动刷新。

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests -v
```

## License

MIT
