from __future__ import annotations

import plistlib
import shutil
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import tomlkit
from tomlkit.exceptions import ParseError

from ..io import atomic_write_bytes, atomic_write_text
from ..models import Theme
from ..paths import CODEX_ACTIVE_THEME, CODEX_CONFIG


THEME_SLUG = "terminal-theme-suite"
DEFAULT_STYLES = {
    "comment": ["italic"],
    "keyword": ["bold"],
    "heading": ["bold"],
    "link": ["underline"],
    "invalid": ["bold"],
}


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.removeprefix("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _mix(base: str, overlay: str, weight: float) -> str:
    mixed = tuple(
        round(base_value * (1 - weight) + overlay_value * weight)
        for base_value, overlay_value in zip(_rgb(base), _rgb(overlay))
    )
    return "#" + "".join(f"{value:02x}" for value in mixed)


def _target(theme: Theme) -> Dict[str, Any]:
    source = theme.extra.get("source", {})
    return dict(source.get("targets", {}).get("codex", {}))


def _roles(theme: Theme) -> Dict[str, str]:
    colors = theme.colors
    roles = {
        "background": colors["background"],
        "foreground": colors["foreground"],
        "caret": colors["accent"],
        "invisibles": colors["dim"],
        "line_highlight": colors["surface"],
        "selection": colors["selection"],
        "gutter": colors["muted"],
        "comment": colors["muted"],
        "string": colors["green"],
        "regex": colors["teal"],
        "number": colors["orange"],
        "constant": colors["cyan"],
        "keyword": colors["accent"],
        "operator": colors["pink"],
        "storage": colors["accent_alt"],
        "type": colors["cyan"],
        "function": colors["blue"],
        "variable": colors["foreground"],
        "parameter": colors["yellow"],
        "property": colors["accent_alt"],
        "tag": colors["blue"],
        "attribute": colors["yellow"],
        "heading": colors["accent"],
        "link": colors["blue"],
        "punctuation": colors["dim"],
        "invalid": colors["red"],
        "diff_added": colors["green"],
        "diff_removed": colors["red"],
        "diff_changed": colors["yellow"],
        "diff_added_background": _mix(colors["background"], colors["green"], 0.22),
        "diff_removed_background": _mix(colors["background"], colors["red"], 0.22),
        "diff_changed_background": _mix(colors["background"], colors["yellow"], 0.18),
    }
    roles.update(_target(theme).get("overrides", {}))
    return roles


def _styles(theme: Theme) -> Dict[str, str]:
    configured = dict(DEFAULT_STYLES)
    configured.update(_target(theme).get("styles", {}))
    return {role: " ".join(attributes) for role, attributes in configured.items()}


def _item(
    name: str,
    scope: str,
    *,
    foreground: Optional[str] = None,
    background: Optional[str] = None,
    font_style: Optional[str] = None,
) -> Dict[str, Any]:
    settings = {}
    if foreground:
        settings["foreground"] = foreground
    if background:
        settings["background"] = background
    if font_style:
        settings["fontStyle"] = font_style
    return {"name": name, "scope": scope, "settings": settings}


def build_theme(theme: Theme) -> Dict[str, Any]:
    roles = _roles(theme)
    styles = _styles(theme)
    settings = [
        {
            "settings": {
                "background": roles["background"],
                "foreground": roles["foreground"],
                "caret": roles["caret"],
                "invisibles": roles["invisibles"],
                "lineHighlight": roles["line_highlight"],
                "selection": roles["selection"],
                "findMatchHighlight": roles["selection"],
                "gutterForeground": roles["gutter"],
            }
        },
        _item(
            "Comments",
            "comment, punctuation.definition.comment",
            foreground=roles["comment"],
            font_style=styles.get("comment"),
        ),
        _item(
            "Strings",
            "string, punctuation.definition.string",
            foreground=roles["string"],
            font_style=styles.get("string"),
        ),
        _item(
            "Regular expressions",
            "string.regexp",
            foreground=roles["regex"],
            font_style=styles.get("regex"),
        ),
        _item(
            "Constants",
            "constant, support.constant",
            foreground=roles["constant"],
            font_style=styles.get("constant"),
        ),
        _item(
            "Numbers",
            "constant.numeric, constant.language.numeric",
            foreground=roles["number"],
            font_style=styles.get("number"),
        ),
        _item(
            "Keywords",
            "keyword, keyword.control, keyword.other",
            foreground=roles["keyword"],
            font_style=styles.get("keyword"),
        ),
        _item(
            "Operators",
            "keyword.operator, keyword.operator.logical",
            foreground=roles["operator"],
            font_style=styles.get("operator"),
        ),
        _item(
            "Storage",
            "storage, storage.type",
            foreground=roles["storage"],
            font_style=styles.get("storage"),
        ),
        _item(
            "Types",
            "entity.name.type, entity.name.class, support.type, support.class",
            foreground=roles["type"],
            font_style=styles.get("type"),
        ),
        _item(
            "Functions",
            "entity.name.function, support.function, variable.function",
            foreground=roles["function"],
            font_style=styles.get("function"),
        ),
        _item(
            "Variables",
            "variable, variable.other, support.variable",
            foreground=roles["variable"],
            font_style=styles.get("variable"),
        ),
        _item(
            "Parameters",
            "variable.parameter",
            foreground=roles["parameter"],
            font_style=styles.get("parameter"),
        ),
        _item(
            "Properties",
            "variable.other.property, support.type.property-name",
            foreground=roles["property"],
            font_style=styles.get("property"),
        ),
        _item(
            "Tags",
            "entity.name.tag",
            foreground=roles["tag"],
            font_style=styles.get("tag"),
        ),
        _item(
            "Attributes",
            "entity.other.attribute-name",
            foreground=roles["attribute"],
            font_style=styles.get("attribute"),
        ),
        _item(
            "Headings",
            "markup.heading, entity.name.section",
            foreground=roles["heading"],
            font_style=styles.get("heading"),
        ),
        _item(
            "Links",
            "markup.underline.link, string.other.link",
            foreground=roles["link"],
            font_style=styles.get("link"),
        ),
        _item(
            "Punctuation",
            "punctuation, meta.brace, meta.delimiter",
            foreground=roles["punctuation"],
            font_style=styles.get("punctuation"),
        ),
        _item(
            "Invalid",
            "invalid, invalid.illegal",
            foreground=roles["invalid"],
            font_style=styles.get("invalid"),
        ),
        _item(
            "Inserted diff",
            "markup.inserted, diff.inserted",
            foreground=roles["diff_added"],
            background=roles["diff_added_background"],
            font_style=styles.get("diff_added"),
        ),
        _item(
            "Deleted diff",
            "markup.deleted, diff.deleted",
            foreground=roles["diff_removed"],
            background=roles["diff_removed_background"],
            font_style=styles.get("diff_removed"),
        ),
        _item(
            "Changed diff",
            "markup.changed, diff.changed",
            foreground=roles["diff_changed"],
            background=roles["diff_changed_background"],
            font_style=styles.get("diff_changed"),
        ),
    ]
    return {
        "name": f"Terminal Theme Suite - {theme.name}",
        "settings": settings,
    }


def serialize_theme(theme: Theme) -> bytes:
    return plistlib.dumps(build_theme(theme), fmt=plistlib.FMT_XML, sort_keys=False)


def _load_config() -> Any:
    original = CODEX_CONFIG.read_text(encoding="utf-8") if CODEX_CONFIG.exists() else ""
    try:
        return tomlkit.parse(original)
    except ParseError as error:
        raise RuntimeError(
            f"Codex config is invalid TOML at {CODEX_CONFIG}: {error}"
        ) from error


def _updated_config() -> tuple[str, bool]:
    document = _load_config()
    tui = document.get("tui")
    if tui is None:
        tui = tomlkit.table()
        document["tui"] = tui
    elif not isinstance(tui, dict):
        raise RuntimeError(f"Codex [tui] config must be a table: {CODEX_CONFIG}")
    already_selected = tui.get("theme") == THEME_SLUG
    tui["theme"] = THEME_SLUG
    return tomlkit.dumps(document), already_selected


def _mode(path: Path) -> int:
    return path.stat().st_mode & 0o777 if path.exists() else 0o644


def _restore(path: Path, previous: Optional[bytes], mode: int) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
    else:
        atomic_write_bytes(path, previous, mode=mode)


def apply_theme(theme: Theme) -> Tuple[str, Optional[str]]:
    config_text, already_selected = _updated_config()
    previous_theme = (
        CODEX_ACTIVE_THEME.read_bytes() if CODEX_ACTIVE_THEME.exists() else None
    )
    previous_config = CODEX_CONFIG.read_bytes() if CODEX_CONFIG.exists() else None
    theme_mode = _mode(CODEX_ACTIVE_THEME)
    config_mode = _mode(CODEX_CONFIG)
    theme_written = False
    config_written = False
    try:
        atomic_write_bytes(CODEX_ACTIVE_THEME, serialize_theme(theme), mode=theme_mode)
        theme_written = True
        if not already_selected:
            atomic_write_text(CODEX_CONFIG, config_text, mode=config_mode)
            config_written = True
    except Exception:
        if theme_written:
            _restore(CODEX_ACTIVE_THEME, previous_theme, theme_mode)
        if config_written:
            _restore(CODEX_CONFIG, previous_config, config_mode)
        raise

    if not shutil.which("codex"):
        warning = (
            "codex is not installed; the managed theme will apply after installation"
        )
    elif already_selected:
        warning = (
            "running Codex TUI sessions do not watch .tmTheme files; reselect "
            "terminal-theme-suite with /theme or restart"
        )
    else:
        warning = (
            "select terminal-theme-suite once with /theme or restart Codex; later "
            "external theme changes still require reselection"
        )
    return f"Codex CLI -> {theme.name} (syntax/diff)", warning


def configuration_status() -> Tuple[bool, str]:
    if not CODEX_ACTIVE_THEME.is_file():
        return False, f"managed theme missing: {CODEX_ACTIVE_THEME}"
    try:
        document = _load_config()
        theme = plistlib.loads(CODEX_ACTIVE_THEME.read_bytes())
    except Exception as error:
        return False, str(error)
    tui = document.get("tui")
    if not isinstance(tui, dict) or tui.get("theme") != THEME_SLUG:
        return False, f"set tui.theme to {THEME_SLUG}"
    if not isinstance(theme, dict) or not isinstance(theme.get("settings"), list):
        return False, f"invalid managed theme: {CODEX_ACTIVE_THEME}"
    return True, f"{THEME_SLUG} -> {CODEX_ACTIVE_THEME}"
