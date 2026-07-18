from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
import re
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
        "hero-amber": {"enabled": True},
        "catppuccin": {"enabled": True},
        "tokyo-night": {"enabled": True},
        "dracula": {"enabled": True},
    },
}

PRESET_SCHEMA_VERSION = 1
PRESET_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".heic"}
PRESET_COLOR_KEYS = {
    "background",
    "background_alt",
    "surface",
    "surface_alt",
    "foreground",
    "muted",
    "dim",
    "accent",
    "accent_alt",
    "red",
    "green",
    "yellow",
    "blue",
    "cyan",
    "teal",
    "orange",
    "pink",
    "selection",
}
_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_PRESET_KEYS = {
    "schema_version",
    "id",
    "order",
    "name",
    "description",
    "license",
    "source_url",
    "author",
    "preview",
    "license_file",
    "wallpaper",
    "ansi",
    "colors",
    "targets",
}


def _theme_resource_paths() -> Iterable[Any]:
    root = resources.files("terminal_theme_suite").joinpath("data", "presets")
    return sorted(
        (
            item.joinpath("preset.json")
            for item in root.iterdir()
            if item.is_dir() and item.joinpath("preset.json").is_file()
        ),
        key=lambda path: path.parent.name,
    )


def _validate_color(value: Any, field: str) -> None:
    if not isinstance(value, str) or not _COLOR_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be a six-digit hex color")


def _validate_local_asset(
    directory: Any, value: Any, field: str, suffixes: set[str]
) -> None:
    if (
        not isinstance(value, str)
        or Path(value).name != value
        or Path(value).suffix.lower() not in suffixes
    ):
        raise ValueError(f"{field} must be a local asset filename")
    if not directory.joinpath(value).is_file():
        raise ValueError(f"{field} does not exist: {value}")


def _validate_preset_document(document: Any, directory: Any) -> None:
    if not isinstance(document, dict):
        raise ValueError(f"{directory}: preset must be a JSON object")
    preset_id = document.get("id", directory.name)
    prefix = f"preset {preset_id}"
    unknown = set(document) - _PRESET_KEYS
    if unknown:
        raise ValueError(f"{prefix}: unknown field(s): {', '.join(sorted(unknown))}")
    if document.get("schema_version") != PRESET_SCHEMA_VERSION:
        raise ValueError(f"{prefix}: schema_version must be {PRESET_SCHEMA_VERSION}")
    if not isinstance(preset_id, str) or not _ID_PATTERN.fullmatch(preset_id):
        raise ValueError(
            f"{prefix}: id must use lowercase letters, numbers, and hyphens"
        )
    if directory.name != preset_id:
        raise ValueError(f"{prefix}: directory name must match id")
    for field in ("name", "description"):
        if not isinstance(document.get(field), str) or not document[field].strip():
            raise ValueError(f"{prefix}: {field} must be a non-empty string")
    for field in ("license", "source_url", "author"):
        if field in document and (
            not isinstance(document[field], str) or not document[field].strip()
        ):
            raise ValueError(f"{prefix}: {field} must be a non-empty string")
    if "preview" in document:
        _validate_local_asset(
            directory, document["preview"], f"{prefix}.preview", PRESET_IMAGE_SUFFIXES
        )
    if "license_file" in document:
        _validate_local_asset(
            directory, document["license_file"], f"{prefix}.license_file", {".txt"}
        )
    if not isinstance(document.get("order"), int) or isinstance(
        document["order"], bool
    ):
        raise ValueError(f"{prefix}: order must be an integer")

    wallpaper = document.get("wallpaper")
    if not isinstance(wallpaper, dict):
        raise ValueError(f"{prefix}: wallpaper must be an object")
    if set(wallpaper) != {"file", "blend", "image_mode"}:
        raise ValueError(
            f"{prefix}: wallpaper requires file, blend, and image_mode only"
        )
    filename = wallpaper.get("file")
    _validate_local_asset(
        directory, filename, f"{prefix}.wallpaper.file", PRESET_IMAGE_SUFFIXES
    )
    blend = wallpaper.get("blend")
    if (
        not isinstance(blend, (int, float))
        or isinstance(blend, bool)
        or not 0 <= blend <= 1
    ):
        raise ValueError(f"{prefix}: wallpaper.blend must be between 0 and 1")
    image_mode = wallpaper.get("image_mode")
    if (
        not isinstance(image_mode, int)
        or isinstance(image_mode, bool)
        or image_mode < 0
    ):
        raise ValueError(
            f"{prefix}: wallpaper.image_mode must be a non-negative integer"
        )

    ansi = document.get("ansi")
    if not isinstance(ansi, list) or len(ansi) != 16:
        raise ValueError(f"{prefix}: ansi must contain exactly 16 colors")
    for index, color in enumerate(ansi):
        _validate_color(color, f"{prefix}.ansi[{index}]")

    colors = document.get("colors")
    if not isinstance(colors, dict):
        raise ValueError(f"{prefix}: colors must be an object")
    missing_colors = PRESET_COLOR_KEYS - set(colors)
    if missing_colors:
        raise ValueError(
            f"{prefix}: missing semantic color(s): {', '.join(sorted(missing_colors))}"
        )
    for name, color in colors.items():
        _validate_color(color, f"{prefix}.colors.{name}")

    targets = document.get("targets")
    if not isinstance(targets, dict) or set(targets) - {"herdr", "omp", "iterm2"}:
        raise ValueError(f"{prefix}: targets contains unsupported integrations")
    herdr = targets.get("herdr")
    if not isinstance(herdr, dict) or set(herdr) != {
        "base_theme",
        "panel_background",
    }:
        raise ValueError(
            f"{prefix}: targets.herdr requires base_theme and panel_background"
        )
    if not all(isinstance(value, str) and value for value in herdr.values()):
        raise ValueError(f"{prefix}: Herdr target values must be non-empty strings")
    omp = targets.get("omp")
    if omp is not None:
        if (
            not isinstance(omp, dict)
            or set(omp) != {"colors"}
            or not isinstance(omp["colors"], dict)
        ):
            raise ValueError(f"{prefix}: targets.omp requires a colors object")
        for name, color in omp["colors"].items():
            _validate_color(color, f"{prefix}.targets.omp.colors.{name}")
    if "iterm2" in targets and not isinstance(targets["iterm2"], dict):
        raise ValueError(f"{prefix}: targets.iterm2 must be an object")


@lru_cache(maxsize=1)
def builtin_theme_documents() -> Dict[str, Dict[str, Any]]:
    loaded: List[Dict[str, Any]] = []
    for path in _theme_resource_paths():
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}: invalid preset JSON: {error.msg}") from error
        _validate_preset_document(document, path.parent)
        document["_preset_directory"] = str(path.parent)
        loaded.append(document)
    loaded.sort(key=lambda item: (int(item.get("order", 100)), item["id"]))
    documents: Dict[str, Dict[str, Any]] = {}
    for document in loaded:
        if document["id"] in documents:
            raise ValueError(f"duplicate preset id: {document['id']}")
        documents[document["id"]] = document
    return documents


def write_default_config(force: bool = False) -> Path:
    ensure_user_dirs()
    if force or not CONFIG_FILE.exists():
        atomic_write_json(CONFIG_FILE, DEFAULT_CONFIG)
    return CONFIG_FILE


def _bundled_background(document: Dict[str, Any]) -> Path | None:
    directory = Path(document["_preset_directory"])
    return (directory / str(document["wallpaper"]["file"])).resolve()


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
        wallpaper = document["wallpaper"]
        targets = document["targets"]
        herdr_target = targets["herdr"]
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
                herdr_theme=str(
                    override.get("herdr_theme", herdr_target["base_theme"])
                ),
                herdr_panel_bg=str(
                    override.get("herdr_panel_bg", herdr_target["panel_background"])
                ),
                background=background,
                blend=float(override.get("blend", wallpaper["blend"])),
                image_mode=int(override.get("image_mode", wallpaper["image_mode"])),
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
