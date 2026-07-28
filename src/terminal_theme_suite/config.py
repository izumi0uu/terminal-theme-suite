from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path
import re
from typing import Any, Dict, Iterable, List

from .io import atomic_write_bytes, atomic_write_json, read_json
from .models import TerminalTypography, Theme, UserConfig
from .paths import BACKGROUND_DIR, CONFIG_FILE, ensure_user_dirs


DEFAULT_CONFIG: Dict[str, Any] = {
    "base_profile_guid": None,
    "scope": "all",
    "shortcuts": True,
    "command_path": None,
    "iterm_daemon": None,
    "terminal_typography": {
        "mode": "inherit",
    },
    "themes": {
        "hero-amber": {"enabled": True},
        "catppuccin": {"enabled": True},
        "tokyo-night": {"enabled": True},
        "dracula": {"enabled": True},
    },
}

_TYPOGRAPHY_KEYS = {
    "mode",
    "font_family",
    "non_ascii_font_family",
    "font_size",
    "horizontal_spacing",
    "vertical_spacing",
    "ligatures",
    "use_bold_font",
    "use_italic_font",
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
CLAUDE_BASE_THEMES = {
    "dark",
    "light",
    "dark-daltonized",
    "light-daltonized",
    "dark-ansi",
    "light-ansi",
}
CLAUDE_COLOR_TOKENS = (
    {
        "claude",
        "text",
        "inverseText",
        "inactive",
        "subtle",
        "suggestion",
        "permission",
        "remember",
        "success",
        "error",
        "warning",
        "merged",
        "promptBorder",
        "planMode",
        "autoAccept",
        "bashBorder",
        "ide",
        "fastMode",
        "diffAdded",
        "diffRemoved",
        "diffAddedDimmed",
        "diffRemovedDimmed",
        "diffAddedWord",
        "diffRemovedWord",
        "userMessageBackground",
        "userMessageBackgroundHover",
        "bashMessageBackgroundColor",
        "memoryBackgroundColor",
        "selectionBg",
        "rate_limit_fill",
        "rate_limit_empty",
        "briefLabelYou",
        "briefLabelClaude",
        "claudeShimmer",
        "warningShimmer",
        "permissionShimmer",
        "promptBorderShimmer",
        "inactiveShimmer",
        "fastModeShimmer",
    }
    | {
        f"{color}_FOR_SUBAGENTS_ONLY"
        for color in (
            "red",
            "blue",
            "green",
            "yellow",
            "purple",
            "orange",
            "pink",
            "cyan",
        )
    }
    | {
        f"rainbow_{color}{suffix}"
        for color in ("red", "orange", "yellow", "green", "blue", "indigo", "violet")
        for suffix in ("", "_shimmer")
    }
)
CODEX_COLOR_ROLES = {
    "background",
    "foreground",
    "caret",
    "invisibles",
    "line_highlight",
    "selection",
    "gutter",
    "comment",
    "string",
    "regex",
    "number",
    "constant",
    "keyword",
    "operator",
    "storage",
    "type",
    "function",
    "variable",
    "parameter",
    "property",
    "tag",
    "attribute",
    "heading",
    "link",
    "punctuation",
    "invalid",
    "diff_added",
    "diff_removed",
    "diff_changed",
    "diff_added_background",
    "diff_removed_background",
    "diff_changed_background",
}
CODEX_STYLE_ROLES = {
    "comment",
    "string",
    "regex",
    "number",
    "constant",
    "keyword",
    "operator",
    "storage",
    "type",
    "function",
    "variable",
    "parameter",
    "property",
    "tag",
    "attribute",
    "heading",
    "link",
    "punctuation",
    "invalid",
    "diff_added",
    "diff_removed",
    "diff_changed",
}
CODEX_FONT_STYLES = {"bold", "italic", "underline"}
HERMES_COLOR_ROLES = {
    "banner_border",
    "banner_title",
    "banner_accent",
    "banner_dim",
    "banner_text",
    "ui_primary",
    "ui_accent",
    "ui_border",
    "ui_text",
    "ui_label",
    "ui_ok",
    "ui_error",
    "ui_warn",
    "prompt",
    "input_rule",
    "response_border",
    "status_bar_bg",
    "status_bar_text",
    "status_bar_strong",
    "status_bar_dim",
    "status_bar_good",
    "status_bar_warn",
    "status_bar_bad",
    "status_bar_critical",
    "session_label",
    "session_border",
    "voice_status_bg",
    "selection_bg",
    "completion_menu_bg",
    "completion_menu_current_bg",
    "completion_menu_meta_bg",
    "completion_menu_meta_current_bg",
    "shell_dollar",
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
    root = resources.files("terminal_theme_suite").joinpath("data").joinpath("presets")
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


def _terminal_typography(value: Any) -> TerminalTypography:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise ValueError("terminal_typography must be an object")
    unknown = set(value) - _TYPOGRAPHY_KEYS
    if unknown:
        raise ValueError(
            "terminal_typography contains unknown field(s): "
            + ", ".join(sorted(unknown))
        )
    mode = value.get("mode", "inherit")
    if mode not in {"inherit", "managed"}:
        raise ValueError("terminal_typography.mode must be inherit or managed")

    font_family = value.get("font_family")
    non_ascii_font_family = value.get("non_ascii_font_family")
    for field, font in (
        ("font_family", font_family),
        ("non_ascii_font_family", non_ascii_font_family),
    ):
        if font is not None and (not isinstance(font, str) or not font.strip()):
            raise ValueError(f"terminal_typography.{field} must be a non-empty string")

    font_size = value.get("font_size")
    if font_size is not None and (
        not isinstance(font_size, (int, float))
        or isinstance(font_size, bool)
        or font_size <= 0
    ):
        raise ValueError("terminal_typography.font_size must be a positive number")
    if mode == "managed" and (not font_family or font_size is None):
        raise ValueError(
            "managed terminal_typography requires font_family and font_size"
        )

    spacing = {}
    for field in ("horizontal_spacing", "vertical_spacing"):
        item = value.get(field, 1.0)
        if not isinstance(item, (int, float)) or isinstance(item, bool) or item <= 0:
            raise ValueError(f"terminal_typography.{field} must be a positive number")
        spacing[field] = float(item)

    flags = {}
    for field, default in (
        ("ligatures", False),
        ("use_bold_font", True),
        ("use_italic_font", True),
    ):
        item = value.get(field, default)
        if not isinstance(item, bool):
            raise ValueError(f"terminal_typography.{field} must be a boolean")
        flags[field] = item

    return TerminalTypography(
        mode=mode,
        font_family=font_family.strip() if font_family else None,
        non_ascii_font_family=(
            non_ascii_font_family.strip() if non_ascii_font_family else None
        ),
        font_size=float(font_size) if font_size is not None else None,
        horizontal_spacing=spacing["horizontal_spacing"],
        vertical_spacing=spacing["vertical_spacing"],
        ligatures=flags["ligatures"],
        use_bold_font=flags["use_bold_font"],
        use_italic_font=flags["use_italic_font"],
    )


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
    if not isinstance(targets, dict) or set(targets) - {
        "herdr",
        "omp",
        "claude",
        "codex",
        "hermes",
    }:
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
    claude = targets.get("claude")
    if claude is not None:
        if (
            not isinstance(claude, dict)
            or set(claude) != {"base", "overrides"}
            or claude.get("base") not in CLAUDE_BASE_THEMES
            or not isinstance(claude.get("overrides"), dict)
        ):
            raise ValueError(
                f"{prefix}: targets.claude requires a supported base and overrides object"
            )
        unknown_tokens = set(claude["overrides"]) - CLAUDE_COLOR_TOKENS
        if unknown_tokens:
            raise ValueError(
                f"{prefix}: targets.claude contains unsupported token(s): "
                + ", ".join(sorted(unknown_tokens))
            )
        for name, color in claude["overrides"].items():
            _validate_color(color, f"{prefix}.targets.claude.overrides.{name}")
    codex = targets.get("codex")
    if codex is not None:
        if (
            not isinstance(codex, dict)
            or "overrides" not in codex
            or set(codex) - {"overrides", "styles"}
            or not isinstance(codex.get("overrides"), dict)
        ):
            raise ValueError(
                f"{prefix}: targets.codex requires overrides and optional styles objects"
            )
        unknown_roles = set(codex["overrides"]) - CODEX_COLOR_ROLES
        if unknown_roles:
            raise ValueError(
                f"{prefix}: targets.codex contains unsupported role(s): "
                + ", ".join(sorted(unknown_roles))
            )
        for name, color in codex["overrides"].items():
            _validate_color(color, f"{prefix}.targets.codex.overrides.{name}")
        styles = codex.get("styles", {})
        if not isinstance(styles, dict):
            raise ValueError(f"{prefix}: targets.codex.styles must be an object")
        unknown_style_roles = set(styles) - CODEX_STYLE_ROLES
        if unknown_style_roles:
            raise ValueError(
                f"{prefix}: targets.codex.styles contains unsupported role(s): "
                + ", ".join(sorted(unknown_style_roles))
            )
        for role, attributes in styles.items():
            if (
                not isinstance(attributes, list)
                or any(
                    not isinstance(attribute, str) or attribute not in CODEX_FONT_STYLES
                    for attribute in attributes
                )
                or len(attributes) != len(set(attributes))
            ):
                raise ValueError(
                    f"{prefix}.targets.codex.styles.{role} must contain unique "
                    "bold, italic, or underline values"
                )
    hermes = targets.get("hermes")
    if hermes is not None:
        if (
            not isinstance(hermes, dict)
            or set(hermes) != {"overrides"}
            or not isinstance(hermes.get("overrides"), dict)
        ):
            raise ValueError(f"{prefix}: targets.hermes requires an overrides object")
        unknown_roles = set(hermes["overrides"]) - HERMES_COLOR_ROLES
        if unknown_roles:
            raise ValueError(
                f"{prefix}: targets.hermes contains unsupported role(s): "
                + ", ".join(sorted(unknown_roles))
            )
        for name, color in hermes["overrides"].items():
            _validate_color(color, f"{prefix}.targets.hermes.overrides.{name}")


@lru_cache(maxsize=1)
def builtin_theme_documents() -> Dict[str, Dict[str, Any]]:
    loaded: List[Dict[str, Any]] = []
    for path in _theme_resource_paths():
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}: invalid preset JSON: {error.msg}") from error
        _validate_preset_document(document, path.parent)
        document["_preset_directory"] = path.parent
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
    filename = str(document["wallpaper"]["file"])
    resource = document["_preset_directory"].joinpath(filename)
    if isinstance(resource, Path):
        return resource.resolve()

    destination = BACKGROUND_DIR / "bundled" / str(document["id"]) / filename
    data = resource.read_bytes()
    if not destination.is_file() or destination.read_bytes() != data:
        atomic_write_bytes(destination, data)
    return destination.resolve()


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
        terminal_typography=_terminal_typography(raw.get("terminal_typography")),
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
