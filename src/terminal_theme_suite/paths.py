from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else default


HOME = Path.home()
CONFIG_DIR = _env_path("TTS_CONFIG_DIR", HOME / ".config" / "terminal-theme-suite")
CONFIG_FILE = CONFIG_DIR / "config.json"
STATE_FILE = CONFIG_DIR / "state.json"
SWITCH_LOCK = CONFIG_DIR / "switch.lock"
BACKGROUND_DIR = CONFIG_DIR / "backgrounds"
BACKUP_DIR = CONFIG_DIR / "backups"

ITERM_APP_SUPPORT = _env_path(
    "TTS_ITERM_APP_SUPPORT", HOME / "Library" / "Application Support" / "iTerm2"
)
ITERM_DYNAMIC_PROFILES = _env_path(
    "TTS_ITERM_DYNAMIC_PROFILES", ITERM_APP_SUPPORT / "DynamicProfiles"
)
ITERM_PROFILE_FILE = ITERM_DYNAMIC_PROFILES / "Terminal Theme Suite.plist"
ITERM_PREFS = _env_path(
    "TTS_ITERM_PREFS", HOME / "Library" / "Preferences" / "com.googlecode.iterm2.plist"
)
ITERM_SCRIPTS_DIR = _env_path(
    "TTS_ITERM_SCRIPTS_DIR",
    HOME / "Library" / "ApplicationSupport" / "iTerm2" / "Scripts",
)
ITERM_API_DAEMON = ITERM_SCRIPTS_DIR / "AutoLaunch" / "terminal_theme_suite.py"
ITERM_RUNTIME_DIR = _env_path(
    "TTS_ITERM_RUNTIME_DIR",
    HOME / "Library" / "ApplicationSupport" / "iTerm2" / "iterm2env",
)
ITERM_RUNTIME_METADATA = ITERM_RUNTIME_DIR / "iterm2env-metadata.json"

OMP_DIR = _env_path("TTS_OMP_DIR", HOME / ".omp" / "agent")
OMP_THEME_DIR = OMP_DIR / "themes"
OMP_ACTIVE_THEME = OMP_THEME_DIR / "terminal-theme-suite.json"
OMP_LIVE_RELOAD_EXTENSION = CONFIG_DIR / "omp-live-reload.ts"
OMP_GENERATION_FILE = CONFIG_DIR / "omp-generation.json"
OMP_RUNTIME_DIR = CONFIG_DIR / "omp-runtime"

HERDR_DIR = _env_path("TTS_HERDR_DIR", HOME / ".config" / "herdr")
HERDR_CONFIG = HERDR_DIR / "config.toml"

CLAUDE_DIR = _env_path("TTS_CLAUDE_DIR", HOME / ".claude")
CLAUDE_SETTINGS = _env_path("TTS_CLAUDE_SETTINGS", CLAUDE_DIR / "settings.json")
CLAUDE_THEME_DIR = _env_path("TTS_CLAUDE_THEME_DIR", CLAUDE_DIR / "themes")
CLAUDE_ACTIVE_THEME = CLAUDE_THEME_DIR / "terminal-theme-suite.json"

CODEX_DIR = _env_path("TTS_CODEX_DIR", _env_path("CODEX_HOME", HOME / ".codex"))
CODEX_CONFIG = _env_path("TTS_CODEX_CONFIG", CODEX_DIR / "config.toml")
CODEX_THEME_DIR = _env_path("TTS_CODEX_THEME_DIR", CODEX_DIR / "themes")
CODEX_ACTIVE_THEME = CODEX_THEME_DIR / "terminal-theme-suite.tmTheme"

HERMES_DIR = _env_path("TTS_HERMES_DIR", _env_path("HERMES_HOME", HOME / ".hermes"))
HERMES_CONFIG = _env_path("TTS_HERMES_CONFIG", HERMES_DIR / "config.yaml")
HERMES_SKIN_DIR = _env_path("TTS_HERMES_SKIN_DIR", HERMES_DIR / "skins")
HERMES_ACTIVE_SKIN = HERMES_SKIN_DIR / "terminal-theme-suite.yaml"


def ensure_user_dirs() -> None:
    for directory in (CONFIG_DIR, BACKGROUND_DIR, BACKUP_DIR, ITERM_DYNAMIC_PROFILES):
        directory.mkdir(parents=True, exist_ok=True)
