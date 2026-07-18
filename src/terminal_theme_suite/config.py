from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .io import atomic_write_json, read_json
from .models import Theme, UserConfig
from .paths import CONFIG_FILE, ensure_user_dirs


DEFAULT_CONFIG: Dict[str, Any] = {
    "base_profile_guid": None,
    "scope": "all",
    "shortcuts": True,
    "command_path": None,
    "iterm_daemon": None,
    "themes": {
        "hero-amber": {"blend": 0.65, "enabled": True},
        "catppuccin": {"blend": 0.65, "enabled": True},
        "tokyo-night": {"blend": 0.65, "enabled": True},
        "dracula": {"blend": 0.65, "enabled": True},
    },
}


def _theme_resource_paths() -> Iterable[Any]:
    root = resources.files("terminal_theme_suite").joinpath("data", "themes")
    return sorted(
        (item for item in root.iterdir() if item.name.endswith(".json")),
        key=lambda p: p.name,
    )


@lru_cache(maxsize=1)
def builtin_theme_documents() -> Dict[str, Dict[str, Any]]:
    loaded: List[Dict[str, Any]] = []
    for path in _theme_resource_paths():
        loaded.append(json.loads(path.read_text(encoding="utf-8")))
    loaded.sort(key=lambda item: (int(item.get("order", 100)), item["id"]))
    documents: Dict[str, Dict[str, Any]] = {}
    for document in loaded:
        documents[document["id"]] = document
    return documents


def write_default_config(force: bool = False) -> Path:
    ensure_user_dirs()
    if force or not CONFIG_FILE.exists():
        atomic_write_json(CONFIG_FILE, DEFAULT_CONFIG)
    return CONFIG_FILE


def _bundled_background(document: Dict[str, Any]) -> Path | None:
    filename = document.get("wallpaper")
    if not filename:
        return None
    resource = resources.files("terminal_theme_suite").joinpath(
        "data", "backgrounds", str(filename)
    )
    return Path(str(resource)).resolve()


def _resolve_background(value: Any, bundled: Path | None) -> Path | None:
    if value is False or value == "":
        return None
    if value is None:
        return bundled
    return Path(str(value)).expanduser().resolve()


def load_config() -> UserConfig:
    write_default_config()
    raw = read_json(CONFIG_FILE, {})
    builtins = builtin_theme_documents()
    overrides = raw.get("themes", {})
    themes: List[Theme] = []

    for theme_id, document in builtins.items():
        override = overrides.get(theme_id, {})
        colors = dict(document["colors"])
        colors.update(override.get("colors", {}))
        ansi = list(override.get("ansi", document["ansi"]))
        background_value = override.get("background")
        bundled_background = _bundled_background(document)
        background = _resolve_background(background_value, bundled_background)
        background_source = (
            "disabled"
            if background is None
            else "bundled"
            if background_value is None
            else "custom"
        )
        themes.append(
            Theme(
                id=theme_id,
                name=str(override.get("name", document["name"])),
                description=str(override.get("description", document["description"])),
                ansi=ansi,
                colors=colors,
                herdr_theme=str(override.get("herdr_theme", document["herdr_theme"])),
                herdr_panel_bg=str(
                    override.get(
                        "herdr_panel_bg", document.get("herdr_panel_bg", "background")
                    )
                ),
                background=background,
                blend=float(override.get("blend", document.get("blend", 0.65))),
                image_mode=int(
                    override.get("image_mode", document.get("image_mode", 2))
                ),
                enabled=bool(override.get("enabled", True)),
                extra={
                    "source": document,
                    "background_source": background_source,
                },
            )
        )

    enabled = [theme for theme in themes if theme.enabled]
    if not enabled:
        raise ValueError("At least one theme must be enabled in config.json")
    return UserConfig(
        themes=enabled,
        base_profile_guid=raw.get("base_profile_guid"),
        scope=str(raw.get("scope", "all")),
        shortcuts=bool(raw.get("shortcuts", True)),
        command_path=raw.get("command_path"),
        iterm_daemon=raw.get("iterm_daemon"),
    )


def update_theme_background(theme_id: str, background: Path | bool | None) -> None:
    write_default_config()
    raw = read_json(CONFIG_FILE, DEFAULT_CONFIG)
    themes = raw.setdefault("themes", {})
    if theme_id not in builtin_theme_documents():
        raise KeyError(theme_id)
    item = themes.setdefault(theme_id, {})
    if background is False:
        item["background"] = False
    elif background is None:
        item.pop("background", None)
    else:
        item["background"] = str(background.expanduser().resolve())
    atomic_write_json(CONFIG_FILE, raw)


def update_iterm_daemon(path: Path) -> None:
    write_default_config()
    raw = read_json(CONFIG_FILE, DEFAULT_CONFIG)
    raw.pop("iterm_runner", None)
    raw["iterm_daemon"] = str(path.expanduser().resolve())
    atomic_write_json(CONFIG_FILE, raw)


def find_theme(config: UserConfig, theme_id: str) -> Theme:
    normalized = theme_id.strip().lower()
    for theme in config.themes:
        if theme.id == normalized or theme.name.lower() == normalized:
            return theme
    raise KeyError(theme_id)
