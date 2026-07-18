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

HERDR_DIR = _env_path("TTS_HERDR_DIR", HOME / ".config" / "herdr")
HERDR_CONFIG = HERDR_DIR / "config.toml"


def ensure_user_dirs() -> None:
    for directory in (CONFIG_DIR, BACKGROUND_DIR, BACKUP_DIR, ITERM_DYNAMIC_PROFILES):
        directory.mkdir(parents=True, exist_ok=True)
