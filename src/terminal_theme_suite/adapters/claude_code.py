from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..io import atomic_write_bytes, atomic_write_json
from ..models import Theme
from ..paths import CLAUDE_ACTIVE_THEME, CLAUDE_SETTINGS, CLAUDE_THEME_DIR


THEME_SLUG = "terminal-theme-suite"
THEME_SETTING = f"custom:{THEME_SLUG}"


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.removeprefix("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _mix(base: str, overlay: str, weight: float) -> str:
    base_rgb = _rgb(base)
    overlay_rgb = _rgb(overlay)
    mixed = tuple(
        round(base_value * (1 - weight) + overlay_value * weight)
        for base_value, overlay_value in zip(base_rgb, overlay_rgb)
    )
    return "#" + "".join(f"{value:02x}" for value in mixed)


def _is_light(color: str) -> bool:
    channels = []
    for value in _rgb(color):
        normalized = value / 255
        channels.append(
            normalized / 12.92
            if normalized <= 0.04045
            else ((normalized + 0.055) / 1.055) ** 2.4
        )
    luminance = 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    return luminance > 0.5


def _target(theme: Theme) -> Dict[str, Any]:
    source = theme.extra.get("source", {})
    return dict(source.get("targets", {}).get("claude", {}))


def _shimmer(color: str, colors: Dict[str, str], light: bool) -> str:
    target = colors["background"] if light else colors["foreground"]
    return _mix(color, target, 0.35)


def _semantic_overrides(theme: Theme, base: str) -> Dict[str, str]:
    colors = theme.colors
    light = base.startswith("light")
    overrides = {
        "claude": colors["accent"],
        "text": colors["foreground"],
        "inverseText": colors["background"],
        "inactive": colors["muted"],
        "subtle": colors["dim"],
        "suggestion": colors["accent_alt"],
        "permission": colors["accent"],
        "remember": colors["pink"],
        "success": colors["green"],
        "error": colors["red"],
        "warning": colors["yellow"],
        "merged": colors["accent"],
        "promptBorder": colors["accent"],
        "planMode": colors["blue"],
        "autoAccept": colors["green"],
        "bashBorder": colors["yellow"],
        "ide": colors["cyan"],
        "fastMode": colors["orange"],
        "diffAdded": _mix(colors["background"], colors["green"], 0.22),
        "diffRemoved": _mix(colors["background"], colors["red"], 0.22),
        "diffAddedDimmed": _mix(colors["background"], colors["green"], 0.10),
        "diffRemovedDimmed": _mix(colors["background"], colors["red"], 0.10),
        "diffAddedWord": _mix(colors["background"], colors["green"], 0.38),
        "diffRemovedWord": _mix(colors["background"], colors["red"], 0.38),
        "userMessageBackground": colors["surface"],
        "userMessageBackgroundHover": colors["surface_alt"],
        "bashMessageBackgroundColor": colors["background_alt"],
        "memoryBackgroundColor": colors["background_alt"],
        "selectionBg": colors["selection"],
        "rate_limit_fill": colors["accent"],
        "rate_limit_empty": colors["surface_alt"],
        "briefLabelYou": colors["accent_alt"],
        "briefLabelClaude": colors["accent"],
        "red_FOR_SUBAGENTS_ONLY": colors["red"],
        "blue_FOR_SUBAGENTS_ONLY": colors["blue"],
        "green_FOR_SUBAGENTS_ONLY": colors["green"],
        "yellow_FOR_SUBAGENTS_ONLY": colors["yellow"],
        "purple_FOR_SUBAGENTS_ONLY": colors["accent"],
        "orange_FOR_SUBAGENTS_ONLY": colors["orange"],
        "pink_FOR_SUBAGENTS_ONLY": colors["pink"],
        "cyan_FOR_SUBAGENTS_ONLY": colors["cyan"],
    }

    shimmer_pairs = {
        "claudeShimmer": "accent",
        "warningShimmer": "yellow",
        "permissionShimmer": "accent",
        "promptBorderShimmer": "accent",
        "inactiveShimmer": "muted",
        "fastModeShimmer": "orange",
    }
    for token, source in shimmer_pairs.items():
        overrides[token] = _shimmer(colors[source], colors, light)

    rainbow = {
        "red": "red",
        "orange": "orange",
        "yellow": "yellow",
        "green": "green",
        "blue": "blue",
        "indigo": "accent_alt",
        "violet": "accent",
    }
    for name, source in rainbow.items():
        overrides[f"rainbow_{name}"] = colors[source]
        overrides[f"rainbow_{name}_shimmer"] = _shimmer(colors[source], colors, light)
    return overrides


def build_theme(theme: Theme) -> Dict[str, Any]:
    target = _target(theme)
    base = str(
        target.get("base", "light" if _is_light(theme.colors["background"]) else "dark")
    )
    overrides = _semantic_overrides(theme, base)
    overrides.update(target.get("overrides", {}))
    return {
        "name": f"Terminal Theme Suite - {theme.name}",
        "base": base,
        "overrides": overrides,
    }


def _load_settings() -> Dict[str, Any]:
    if not CLAUDE_SETTINGS.exists():
        return {}
    try:
        document = json.loads(CLAUDE_SETTINGS.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"Claude settings are invalid JSON at {CLAUDE_SETTINGS}: {error.msg}"
        ) from error
    if not isinstance(document, dict):
        raise RuntimeError(f"Claude settings must be a JSON object: {CLAUDE_SETTINGS}")
    return document


def _mode(path: Path) -> int:
    return path.stat().st_mode & 0o777 if path.exists() else 0o644


def _restore(path: Path, previous: Optional[bytes], mode: int) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
    else:
        atomic_write_bytes(path, previous, mode=mode)


def apply_theme(theme: Theme) -> Tuple[str, Optional[str]]:
    directory_existed = CLAUDE_THEME_DIR.is_dir()
    settings = _load_settings()
    already_selected = settings.get("theme") == THEME_SETTING
    settings["theme"] = THEME_SETTING

    previous_theme = (
        CLAUDE_ACTIVE_THEME.read_bytes() if CLAUDE_ACTIVE_THEME.exists() else None
    )
    previous_settings = (
        CLAUDE_SETTINGS.read_bytes() if CLAUDE_SETTINGS.exists() else None
    )
    theme_mode = _mode(CLAUDE_ACTIVE_THEME)
    settings_mode = _mode(CLAUDE_SETTINGS)
    theme_written = False
    settings_written = False
    try:
        atomic_write_json(CLAUDE_ACTIVE_THEME, build_theme(theme), mode=theme_mode)
        theme_written = True
        if not already_selected:
            atomic_write_json(CLAUDE_SETTINGS, settings, mode=settings_mode)
            settings_written = True
    except Exception:
        if theme_written:
            _restore(CLAUDE_ACTIVE_THEME, previous_theme, theme_mode)
        if settings_written:
            _restore(CLAUDE_SETTINGS, previous_settings, settings_mode)
        raise

    warning = None
    if not shutil.which("claude"):
        warning = (
            "claude is not installed; the managed theme will apply after installation"
        )
    elif not directory_existed:
        warning = (
            "restart any running Claude Code session once; future theme switches "
            "will hot-reload"
        )
    elif not already_selected:
        warning = (
            "select terminal-theme-suite once with /theme or restart the running "
            "Claude Code session"
        )
    return f"Claude Code -> {theme.name}", warning


def configuration_status() -> Tuple[bool, str]:
    if not CLAUDE_ACTIVE_THEME.is_file():
        return False, f"managed theme missing: {CLAUDE_ACTIVE_THEME}"
    try:
        settings = _load_settings()
        theme = json.loads(CLAUDE_ACTIVE_THEME.read_text(encoding="utf-8"))
    except (RuntimeError, json.JSONDecodeError) as error:
        return False, str(error)
    if settings.get("theme") != THEME_SETTING:
        return False, f"set theme to {THEME_SETTING}"
    if not isinstance(theme, dict) or not isinstance(theme.get("overrides"), dict):
        return False, f"invalid managed theme: {CLAUDE_ACTIVE_THEME}"
    return True, f"{THEME_SETTING} -> {CLAUDE_ACTIVE_THEME}"
