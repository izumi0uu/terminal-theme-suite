from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any, Dict, Tuple

from ..io import atomic_write_text
from ..models import Theme
from ..paths import OMP_ACTIVE_THEME


OMP_THEME_SCHEMA = (
    "https://raw.githubusercontent.com/can1357/oh-my-pi/main/"
    "packages/coding-agent/src/modes/theme/theme-schema.json"
)


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


def apply_theme(theme: Theme) -> Tuple[str, str | None]:
    document = build_theme(theme)
    atomic_write_text(OMP_ACTIVE_THEME, json.dumps(document, indent=2) + "\n")
    executable = shutil.which("omp")
    if not executable:
        return "OMP theme file updated", "omp is not installed; skipped config update"

    previous = {}
    for key in ("theme.dark", "theme.light", "symbolPreset"):
        previous[key] = subprocess.run(
            [executable, "config", "get", key],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    for key, value in (
        ("theme.dark", "terminal-theme-suite"),
        ("theme.light", "terminal-theme-suite"),
        ("symbolPreset", "nerd"),
    ):
        result = subprocess.run(
            [executable, "config", "set", key, value],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                result.stderr.strip()
                or result.stdout.strip()
                or f"Unable to update OMP {key}"
            )
    warning = None
    if any(
        previous[key] != "terminal-theme-suite" for key in ("theme.dark", "theme.light")
    ):
        warning = (
            "Restart each already-running OMP once to enable future live theme reloads"
        )
    return "OMP -> terminal-theme-suite (dark/light, Nerd Font)", warning
