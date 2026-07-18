from __future__ import annotations

import shutil
import subprocess
from typing import Optional, Tuple

import tomlkit

from ..io import atomic_write_text
from ..models import Theme
from ..paths import HERDR_CONFIG


CUSTOM_COLOR_MAP = {
    "panel_bg": "background",
    "surface0": "surface",
    "surface1": "surface_alt",
    "surface_dim": "background_alt",
    "overlay0": "dim",
    "overlay1": "muted",
    "text": "foreground",
    "subtext0": "muted",
    "mauve": "accent",
    "green": "green",
    "yellow": "yellow",
    "red": "red",
    "blue": "blue",
    "teal": "teal",
    "peach": "orange",
    "accent": "accent",
}


def _updated_document(theme: Theme) -> str:
    original = HERDR_CONFIG.read_text(encoding="utf-8") if HERDR_CONFIG.exists() else ""
    document = tomlkit.parse(original)
    table = document.get("theme")
    if table is None or not isinstance(table, dict):
        table = tomlkit.table()
        document["theme"] = table
    table["name"] = theme.herdr_theme
    table["auto_switch"] = False
    table.pop("dark_name", None)
    table.pop("light_name", None)
    custom = tomlkit.table()
    for target, source in CUSTOM_COLOR_MAP.items():
        custom[target] = theme.colors[source]
    custom["panel_bg"] = (
        theme.herdr_panel_bg
        if theme.herdr_panel_bg == "reset"
        else theme.colors.get(theme.herdr_panel_bg, theme.herdr_panel_bg)
    )
    table["custom"] = custom
    return tomlkit.dumps(document)


def apply_theme(theme: Theme) -> Tuple[str, Optional[str]]:
    previous = HERDR_CONFIG.read_bytes() if HERDR_CONFIG.exists() else None
    atomic_write_text(HERDR_CONFIG, _updated_document(theme))
    executable = shutil.which("herdr")
    if not executable:
        return "Herdr config updated", "herdr is not installed; skipped live reload"

    check = subprocess.run(
        [executable, "config", "check"], capture_output=True, text=True, check=False
    )
    if check.returncode != 0:
        if previous is None:
            HERDR_CONFIG.unlink(missing_ok=True)
        else:
            HERDR_CONFIG.write_bytes(previous)
        raise RuntimeError(
            check.stderr.strip() or check.stdout.strip() or "Herdr rejected config.toml"
        )

    reload_result = subprocess.run(
        [executable, "server", "reload-config"],
        capture_output=True,
        text=True,
        check=False,
    )
    warning = None
    if reload_result.returncode != 0:
        warning = "Herdr is not running; its theme will apply on the next launch"
    return f"Herdr -> {theme.herdr_theme}", warning
