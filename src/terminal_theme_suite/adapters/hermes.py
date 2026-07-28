from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from ..io import atomic_write_bytes, atomic_write_text
from ..models import Theme
from ..paths import HERMES_ACTIVE_SKIN, HERMES_CONFIG


THEME_SLUG = "terminal-theme-suite"


def _target(theme: Theme) -> Dict[str, Any]:
    source = theme.extra.get("source", {})
    return dict(source.get("targets", {}).get("hermes", {}))


def _colors(theme: Theme) -> Dict[str, str]:
    colors = theme.colors
    roles = {
        "banner_border": colors["accent"],
        "banner_title": colors["accent"],
        "banner_accent": colors["accent_alt"],
        "banner_dim": colors["muted"],
        "banner_text": colors["foreground"],
        "ui_primary": colors["accent"],
        "ui_accent": colors["accent_alt"],
        "ui_border": colors["accent"],
        "ui_text": colors["foreground"],
        "ui_label": colors["cyan"],
        "ui_ok": colors["green"],
        "ui_error": colors["red"],
        "ui_warn": colors["yellow"],
        "prompt": colors["foreground"],
        "input_rule": colors["accent"],
        "response_border": colors["accent"],
        "status_bar_bg": colors["surface"],
        "status_bar_text": colors["foreground"],
        "status_bar_strong": colors["accent"],
        "status_bar_dim": colors["muted"],
        "status_bar_good": colors["green"],
        "status_bar_warn": colors["yellow"],
        "status_bar_bad": colors["orange"],
        "status_bar_critical": colors["red"],
        "session_label": colors["accent_alt"],
        "session_border": colors["dim"],
        "voice_status_bg": colors["surface"],
        "selection_bg": colors["selection"],
        "completion_menu_bg": colors["surface"],
        "completion_menu_current_bg": colors["selection"],
        "completion_menu_meta_bg": colors["surface_alt"],
        "completion_menu_meta_current_bg": colors["selection"],
        "shell_dollar": colors["green"],
    }
    roles.update(_target(theme).get("overrides", {}))
    return roles


def build_skin(theme: Theme) -> Dict[str, Any]:
    return {
        "name": THEME_SLUG,
        "description": f"Terminal Theme Suite - {theme.name}",
        "colors": _colors(theme),
    }


def _serialize(value: Dict[str, Any]) -> str:
    return yaml.safe_dump(
        value,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


def serialize_skin(theme: Theme) -> str:
    return _serialize(build_skin(theme))


def _load_config() -> Dict[str, Any]:
    if not HERMES_CONFIG.exists():
        return {}
    try:
        document = yaml.safe_load(HERMES_CONFIG.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise RuntimeError(
            f"Hermes config is invalid YAML at {HERMES_CONFIG}: {error}"
        ) from error
    if document is None:
        return {}
    if not isinstance(document, dict):
        raise RuntimeError(f"Hermes config must be a mapping: {HERMES_CONFIG}")
    return document


def _updated_config() -> tuple[str, bool]:
    document = _load_config()
    display = document.get("display")
    if display is None:
        display = {}
        document["display"] = display
    elif not isinstance(display, dict):
        raise RuntimeError(f"Hermes display config must be a mapping: {HERMES_CONFIG}")
    already_selected = display.get("skin") == THEME_SLUG
    display["skin"] = THEME_SLUG
    return _serialize(document), already_selected


def _mode(path: Path) -> int:
    return path.stat().st_mode & 0o777 if path.exists() else 0o600


def _restore(path: Path, previous: Optional[bytes], mode: int) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
    else:
        atomic_write_bytes(path, previous, mode=mode)


def apply_theme(theme: Theme) -> Tuple[str, Optional[str]]:
    config_text, already_selected = _updated_config()
    previous_skin = (
        HERMES_ACTIVE_SKIN.read_bytes() if HERMES_ACTIVE_SKIN.exists() else None
    )
    previous_config = HERMES_CONFIG.read_bytes() if HERMES_CONFIG.exists() else None
    skin_mode = _mode(HERMES_ACTIVE_SKIN)
    config_mode = _mode(HERMES_CONFIG)
    skin_written = False
    config_written = False
    try:
        atomic_write_text(HERMES_ACTIVE_SKIN, serialize_skin(theme), mode=skin_mode)
        skin_written = True
        if not already_selected:
            atomic_write_text(HERMES_CONFIG, config_text, mode=config_mode)
            config_written = True
    except Exception:
        if skin_written:
            _restore(HERMES_ACTIVE_SKIN, previous_skin, skin_mode)
        if config_written:
            _restore(HERMES_CONFIG, previous_config, config_mode)
        raise

    if not shutil.which("hermes"):
        warning = (
            "hermes is not installed; the managed skin will apply after installation"
        )
    elif already_selected:
        warning = (
            "running Hermes sessions do not watch skin files; run /skin "
            "terminal-theme-suite or restart"
        )
    else:
        warning = (
            "run /skin terminal-theme-suite in running Hermes sessions or restart; "
            "later external skin changes still require /skin reload"
        )
    return f"Hermes CLI -> {theme.name}", warning


def configuration_status() -> Tuple[bool, str]:
    if not HERMES_ACTIVE_SKIN.is_file():
        return False, f"managed skin missing: {HERMES_ACTIVE_SKIN}"
    try:
        config = _load_config()
        skin = yaml.safe_load(HERMES_ACTIVE_SKIN.read_text(encoding="utf-8"))
    except Exception as error:
        return False, str(error)
    display = config.get("display")
    if not isinstance(display, dict) or display.get("skin") != THEME_SLUG:
        return False, f"set display.skin to {THEME_SLUG}"
    if (
        not isinstance(skin, dict)
        or skin.get("name") != THEME_SLUG
        or not isinstance(skin.get("colors"), dict)
    ):
        return False, f"invalid managed skin: {HERMES_ACTIVE_SKIN}"
    return True, f"{THEME_SLUG} -> {HERMES_ACTIVE_SKIN}"
