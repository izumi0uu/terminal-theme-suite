from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import shutil
from typing import List, Optional

from .adapters import herdr, iterm2, omp
from .config import find_theme, load_config
from .io import atomic_write_json, read_json
from .models import Theme, UserConfig
from .paths import (
    BACKUP_DIR,
    HERDR_CONFIG,
    ITERM_PROFILE_FILE,
    OMP_ACTIVE_THEME,
    OMP_DIR,
    STATE_FILE,
)


@dataclass
class SwitchResult:
    theme: Theme
    messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def _backup_once() -> List[str]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    sources = (
        (OMP_DIR / "config.yml", "omp-config.yml"),
        (OMP_ACTIVE_THEME, "omp-active-theme.json"),
        (HERDR_CONFIG, "herdr-config.toml"),
    )
    created = []
    for source, name in sources:
        destination = BACKUP_DIR / name
        if source.exists() and not destination.exists():
            shutil.copy2(source, destination)
            created.append(str(destination))
    return created


def current_theme_id(config: Optional[UserConfig] = None) -> str:
    config = config or load_config()
    state = read_json(STATE_FILE, {}) or {}
    value = state.get("theme")
    if value and any(theme.id == value for theme in config.themes):
        return str(value)
    return config.themes[0].id


def adjacent_theme(direction: int, config: Optional[UserConfig] = None) -> Theme:
    config = config or load_config()
    current = current_theme_id(config)
    ids = [theme.id for theme in config.themes]
    index = ids.index(current) if current in ids else 0
    return config.themes[(index + direction) % len(config.themes)]


def sync(active_theme_id: Optional[str] = None) -> str:
    config = load_config()
    active = active_theme_id or current_theme_id(config)
    return str(iterm2.sync_profiles(config, active))


def apply(theme_id: str, dry_run: bool = False) -> SwitchResult:
    config = load_config()
    theme = find_theme(config, theme_id)
    result = SwitchResult(theme=theme)
    if dry_run:
        result.messages.append(f"Would switch to {theme.id}")
        return result

    for backup in _backup_once():
        result.messages.append(f"Backup -> {backup}")

    if ITERM_PROFILE_FILE.exists():
        result.messages.append(f"Profiles -> {ITERM_PROFILE_FILE}")
    else:
        result.messages.append(f"Profiles -> {iterm2.sync_profiles(config, theme.id)}")
    result.messages.append(
        iterm2.apply_profile(
            theme.profile_name, iterm2.theme_profile_guid(theme), config.scope
        )
    )

    omp_message, omp_warning = omp.apply_theme(theme)
    result.messages.append(omp_message)
    if omp_warning:
        result.warnings.append(omp_warning)

    herdr_message, herdr_warning = herdr.apply_theme(theme)
    result.messages.append(herdr_message)
    if herdr_warning:
        result.warnings.append(herdr_warning)

    atomic_write_json(
        STATE_FILE,
        {
            "theme": theme.id,
            "profile_guid": iterm2.theme_profile_guid(theme),
            "profile_name": theme.profile_name,
            "scope": config.scope,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return result
