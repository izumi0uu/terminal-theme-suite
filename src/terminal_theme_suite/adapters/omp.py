from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from ..io import atomic_write_text
from ..models import Theme
from ..paths import OMP_ACTIVE_THEME, OMP_LIVE_RELOAD_EXTENSION


OMP_THEME_SCHEMA = (
    "https://raw.githubusercontent.com/can1357/oh-my-pi/main/"
    "packages/coding-agent/src/modes/theme/theme-schema.json"
)


def _run(executable: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [executable, *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def _extensions(executable: str) -> List[str]:
    result = _run(executable, "config", "get", "extensions")
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Unable to read OMP extensions"
        )
    try:
        value = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as error:
        raise RuntimeError("OMP returned an invalid extensions setting") from error
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuntimeError("OMP extensions setting must be a list of paths")
    return value


def _same_path(value: str, target: Path) -> bool:
    return Path(value).expanduser().resolve() == target.expanduser().resolve()


def _set_extensions(executable: str, extensions: List[str]) -> None:
    result = _run(
        executable,
        "config",
        "set",
        "extensions",
        json.dumps(extensions),
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "Unable to update OMP extensions"
        )


def _extension_source() -> str:
    resource = resources.files("terminal_theme_suite").joinpath(
        "data", "omp", "terminal-theme-suite.ts"
    )
    return resource.read_text(encoding="utf-8")


def install_live_reload_extension(executable: Optional[str] = None) -> bool:
    """Install the OMP startup hook. Return True when it was newly registered."""
    executable = executable or shutil.which("omp")
    if not executable:
        return False
    atomic_write_text(OMP_LIVE_RELOAD_EXTENSION, _extension_source())
    extensions = _extensions(executable)
    if any(_same_path(item, OMP_LIVE_RELOAD_EXTENSION) for item in extensions):
        return False
    _set_extensions(executable, [*extensions, str(OMP_LIVE_RELOAD_EXTENSION)])
    return True


def remove_live_reload_extension(executable: Optional[str] = None) -> bool:
    executable = executable or shutil.which("omp")
    removed = False
    if executable:
        extensions = _extensions(executable)
        updated = [
            item
            for item in extensions
            if not _same_path(item, OMP_LIVE_RELOAD_EXTENSION)
        ]
        if updated != extensions:
            _set_extensions(executable, updated)
            removed = True
    if OMP_LIVE_RELOAD_EXTENSION.exists():
        OMP_LIVE_RELOAD_EXTENSION.unlink()
        removed = True
    return removed


def live_reload_status(executable: Optional[str] = None) -> Tuple[bool, str]:
    executable = executable or shutil.which("omp")
    if not executable:
        return False, "OMP is not installed"
    registered = any(
        _same_path(item, OMP_LIVE_RELOAD_EXTENSION) for item in _extensions(executable)
    )
    installed = OMP_LIVE_RELOAD_EXTENSION.is_file() and registered
    return installed, str(OMP_LIVE_RELOAD_EXTENSION)


def configuration_status(executable: Optional[str] = None) -> Tuple[bool, str]:
    executable = executable or shutil.which("omp")
    if not executable:
        return False, "OMP is not installed"
    reload_ready, detail = live_reload_status(executable)
    expected = {
        "theme.dark": "terminal-theme-suite",
        "theme.light": "terminal-theme-suite",
        "symbolPreset": "nerd",
    }
    drift = [
        key
        for key, value in expected.items()
        if _run(executable, "config", "get", key).stdout.strip() != value
    ]
    if not reload_ready:
        drift.append("extensions")
    if drift:
        return False, f"run term-theme repair ({', '.join(drift)})"
    return True, detail


def build_theme(theme: Theme) -> Dict[str, Any]:
    color = theme.colors
    colors = {
        "accent": color["accent"],
        "border": color["accent_alt"],
        "borderAccent": color["accent"],
        "borderMuted": color["surface"],
        "success": color["green"],
        "error": color["red"],
        "warning": color["yellow"],
        "muted": color["muted"],
        "dim": color["dim"],
        "text": color["foreground"],
        "thinkingText": color["muted"],
        "selectedBg": color["selection"],
        "userMessageBg": color["background_alt"],
        "userMessageText": color["foreground"],
        "customMessageBg": color["surface"],
        "customMessageText": color["foreground"],
        "customMessageLabel": color["accent"],
        "toolPendingBg": color["surface"],
        "toolSuccessBg": color["background_alt"],
        "toolErrorBg": color["background_alt"],
        "toolTitle": color["accent"],
        "toolOutput": color["muted"],
        "mdHeading": color["accent"],
        "mdLink": color["cyan"],
        "mdLinkUrl": color["dim"],
        "mdCode": color["pink"],
        "mdCodeBlock": color["foreground"],
        "mdCodeBlockBorder": color["surface"],
        "mdQuote": color["muted"],
        "mdQuoteBorder": color["surface"],
        "mdHr": color["surface"],
        "mdListBullet": color["accent"],
        "toolDiffAdded": color["green"],
        "toolDiffRemoved": color["red"],
        "toolDiffContext": color["muted"],
        "syntaxComment": color["muted"],
        "syntaxKeyword": color["accent"],
        "syntaxFunction": color["blue"],
        "syntaxVariable": color["foreground"],
        "syntaxString": color["green"],
        "syntaxNumber": color["orange"],
        "syntaxType": color["yellow"],
        "syntaxOperator": color["cyan"],
        "syntaxPunctuation": color["foreground"],
        "thinkingOff": color["surface"],
        "thinkingMinimal": color["dim"],
        "thinkingLow": color["blue"],
        "thinkingMedium": color["cyan"],
        "thinkingHigh": color["accent"],
        "thinkingXhigh": color["pink"],
        "bashMode": color["teal"],
        "statusLineBg": color["background_alt"],
        "statusLineSep": color["surface_alt"],
        "statusLineModel": color["accent"],
        "statusLinePath": color["cyan"],
        "statusLineGitClean": color["green"],
        "statusLineGitDirty": color["yellow"],
        "statusLineContext": color["accent_alt"],
        "statusLineSpend": color["teal"],
        "statusLineStaged": color["green"],
        "statusLineDirty": color["orange"],
        "statusLineUntracked": color["cyan"],
        "statusLineOutput": color["pink"],
        "statusLineCost": color["pink"],
        "statusLineSubagents": color["orange"],
        "pythonMode": color["yellow"],
    }
    colors.update(theme.extra.get("source", {}).get("omp_colors", {}))
    return {
        "$schema": OMP_THEME_SCHEMA,
        "name": "terminal-theme-suite",
        "colors": colors,
        "export": {
            "pageBg": color["background"],
            "cardBg": color["background_alt"],
            "infoBg": color["surface"],
        },
    }


def _write_theme(theme: Theme) -> None:
    document = build_theme(theme)
    atomic_write_text(OMP_ACTIVE_THEME, json.dumps(document, indent=2) + "\n")


def configure_theme(theme: Theme) -> Tuple[str, str | None]:
    _write_theme(theme)
    executable = shutil.which("omp")
    if not executable:
        return "OMP theme file updated", "omp is not installed; skipped config update"

    extension_added = install_live_reload_extension(executable)
    for key, value in (
        ("theme.dark", "terminal-theme-suite"),
        ("theme.light", "terminal-theme-suite"),
        ("symbolPreset", "nerd"),
    ):
        result = _run(executable, "config", "set", key, value)
        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or result.stdout.strip()
                or f"Unable to update OMP {key}"
            )
    warning = (
        "Restart currently running OMP processes once to load the live-reload extension"
        if extension_added
        else None
    )
    return "OMP configured -> terminal-theme-suite (dark/light, Nerd Font)", warning


def apply_theme(theme: Theme) -> Tuple[str, str | None]:
    _write_theme(theme)
    return "OMP theme file updated (live reload)", None
