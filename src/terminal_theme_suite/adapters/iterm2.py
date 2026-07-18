from __future__ import annotations

import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from ..io import atomic_write_bytes
from ..models import Theme, UserConfig
from ..paths import ITERM_PREFS, ITERM_PROFILE_FILE


PROFILE_NAMESPACE = uuid.UUID("a26baf13-89e8-488b-8243-e754c9303ef7")
NEXT_SHORTCUT = "0x74-0xc0000"  # Control+Option+T
PREVIOUS_SHORTCUT = "0x74-0xe0000"  # Control+Option+Shift+T
NEW_TAB_SHORTCUT = "0x74-0x100000"  # Command+T
NEW_WINDOW_SHORTCUT = "0x6e-0x100000"  # Command+N
RUN_COPROCESS_ACTION = 35
DAEMON_FUNCTION = "terminal_theme_suite_switch"
PASSTHROUGH_KEYS = {
    "Normal Font",
    "Non Ascii Font",
    "Horizontal Spacing",
    "Vertical Spacing",
    "Unlimited Scrollback",
    "Scrollback Lines",
    "Load Shell Integration Automatically",
    "Working Directory",
    "Custom Directory",
    "Initial Text",
    "Command",
    "Custom Command",
    "Title Components",
    "ASCII Ligatures",
    "Non-ASCII Ligatures",
    "Use Bold Font",
    "Use Bright Bold",
    "Use Italic Font",
    "Blinking Cursor",
    "Cursor Type",
}


def _hex_color(value: str) -> Dict[str, Any]:
    raw = value.lstrip("#")
    if len(raw) != 6:
        raise ValueError(f"Expected #rrggbb color, got {value!r}")
    red, green, blue = (int(raw[index : index + 2], 16) / 255 for index in (0, 2, 4))
    return {
        "Red Component": red,
        "Green Component": green,
        "Blue Component": blue,
        "Alpha Component": 1.0,
        "Color Space": "sRGB",
    }


def _load_preferences() -> Dict[str, Any]:
    try:
        with ITERM_PREFS.open("rb") as handle:
            return plistlib.load(handle)
    except (FileNotFoundError, plistlib.InvalidFileException, OSError):
        return {}


def _source_profile() -> Optional[Dict[str, Any]]:
    preferences = _load_preferences()
    profiles = preferences.get("New Bookmarks", [])
    default_guid = preferences.get("Default Bookmark Guid")
    selected = next(
        (profile for profile in profiles if profile.get("Guid") == default_guid), None
    )
    if selected:
        return selected
    candidates = [
        profile
        for profile in profiles
        if not str(profile.get("Name", "")).startswith("TTS - ")
    ]
    selected = next(
        (profile for profile in candidates if profile.get("Default Bookmark") == "Yes"),
        None,
    )
    selected = selected or (candidates[0] if candidates else None)
    return selected


def discover_base_profile_guid(explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        return explicit
    selected = _source_profile()
    if not selected:
        return None
    return selected.get("Dynamic Profile Parent GUID") or selected.get("Guid")


def _source_overrides() -> Dict[str, Any]:
    source = _source_profile() or {}
    return {key: deepcopy(source[key]) for key in PASSTHROUGH_KEYS if key in source}


def _command_path(config: UserConfig) -> str:
    override = os.environ.get("TTS_COMMAND_PATH") or config.command_path
    if override:
        return str(Path(override).expanduser())
    discovered = shutil.which("term-theme")
    if discovered:
        return discovered
    return str(Path(sys.argv[0]).resolve())


def _base_keyboard_map(base_guid: Optional[str]) -> Dict[str, Dict[str, Any]]:
    profiles = _load_preferences().get("New Bookmarks", [])
    mappings: Dict[str, Dict[str, Any]] = {}
    if base_guid:
        base = next((item for item in profiles if item.get("Guid") == base_guid), None)
        if base:
            mappings.update(deepcopy(base.get("Keyboard Map", {})))
    source = _source_profile()
    if source and not str(source.get("Name", "")).startswith("TTS - "):
        mappings.update(deepcopy(source.get("Keyboard Map", {})))
    return mappings


def _keyboard_map(
    config: UserConfig, base_guid: Optional[str]
) -> Dict[str, Dict[str, Any]]:
    mappings = _base_keyboard_map(base_guid)
    if not config.shortcuts:
        return mappings
    executable = shlex.quote(_command_path(config))
    mappings.update(
        {
            NEXT_SHORTCUT: {
                "Action": RUN_COPROCESS_ACTION,
                "Text": f"{executable} next --quiet",
                "Label": "Terminal Theme Suite: next theme",
            },
            PREVIOUS_SHORTCUT: {
                "Action": RUN_COPROCESS_ACTION,
                "Text": f"{executable} previous --quiet",
                "Label": "Terminal Theme Suite: previous theme",
            },
        }
    )
    return mappings


def _profile(
    theme: Theme, config: UserConfig, active_theme_id: Optional[str]
) -> Dict[str, Any]:
    if len(theme.ansi) != 16:
        raise ValueError(f"Theme {theme.id!r} must define exactly 16 ANSI colors")
    colors = theme.colors
    base_guid = discover_base_profile_guid(config.base_profile_guid)
    profile_guid = theme_profile_guid(theme)
    profile: Dict[str, Any] = _source_overrides()
    profile.update(
        {
            "Name": theme.profile_name,
            "Guid": profile_guid,
            "Rewritable": True,
            "Use Separate Colors for Light and Dark Mode": False,
            "Background Color": _hex_color(colors["background"]),
            "Foreground Color": _hex_color(colors["foreground"]),
            "Bold Color": _hex_color(colors["foreground"]),
            "Cursor Color": _hex_color(colors["accent"]),
            "Cursor Text Color": _hex_color(colors["background"]),
            "Selection Color": _hex_color(colors["selection"]),
            "Selected Text Color": _hex_color(colors["foreground"]),
            "Link Color": _hex_color(colors["cyan"]),
            "Keyboard Map": _keyboard_map(config, base_guid),
        }
    )
    if base_guid:
        profile["Dynamic Profile Parent GUID"] = base_guid
    for index, value in enumerate(theme.ansi):
        profile[f"Ansi {index} Color"] = _hex_color(value)
    if theme.background:
        profile.update(
            {
                "Background Image Location": str(theme.background),
                "Background Image Mode": theme.image_mode,
                "Background Image Source Mode": 0,
                "Blend": theme.blend,
            }
        )
    else:
        profile["Background Image Location"] = ""
    return profile


def theme_profile_guid(theme: Theme) -> str:
    return str(uuid.uuid5(PROFILE_NAMESPACE, theme.id)).upper()


def sync_profiles(config: UserConfig, active_theme_id: Optional[str]) -> Path:
    document = {
        "Profiles": [
            _profile(theme, config, active_theme_id) for theme in config.themes
        ]
    }
    data = plistlib.dumps(document, fmt=plistlib.FMT_XML, sort_keys=False)
    atomic_write_bytes(ITERM_PROFILE_FILE, data)
    return ITERM_PROFILE_FILE


def _iterm_is_running() -> bool:
    if sys.platform != "darwin":
        return False
    result = subprocess.run(
        ["osascript", "-e", 'application "iTerm2" is running'],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def enable_api() -> None:
    result = subprocess.run(
        [
            "defaults",
            "write",
            "com.googlecode.iterm2",
            "EnableAPIServer",
            "-bool",
            "true",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to enable the iTerm2 API")


def _set_persistent_default(profile_guid: str) -> None:
    result = subprocess.run(
        [
            "defaults",
            "write",
            "com.googlecode.iterm2",
            "Default Bookmark Guid",
            "-string",
            profile_guid,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Unable to update iTerm2 default profile"
        )


def _invoke_expression(expression: str, timeout: int = 15) -> str:
    escaped = expression.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "iTerm2" to invoke API expression "{escaped}"'
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("iTerm2 theme daemon did not respond") from error
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "iTerm2 theme daemon is unavailable; restart iTerm2 after installation"
            + (f". Details: {detail}" if detail else "")
        )
    return result.stdout.strip()


def _invoke_daemon(profile_guid: str, scope: str) -> None:
    expression = f'{DAEMON_FUNCTION}(profile_guid: "{profile_guid}", scope: "{scope}")'
    _invoke_expression(expression)


def daemon_ready() -> bool:
    if not _iterm_is_running():
        return False
    try:
        return _invoke_expression("terminal_theme_suite_ping()", timeout=3) == "ready"
    except RuntimeError:
        return False


def apply_profile(profile_name: str, profile_guid: str, scope: str = "all") -> str:
    if sys.platform != "darwin":
        return "iTerm2 profile generated; live switching is only available on macOS"
    if scope not in {"all", "current"}:
        raise ValueError("scope must be 'all' or 'current'")
    if not _iterm_is_running():
        _set_persistent_default(profile_guid)
        return (
            "iTerm2 default profile updated; live switching will apply when it starts"
        )
    _invoke_daemon(profile_guid, scope)
    _set_persistent_default(profile_guid)
    return f"iTerm2 -> {profile_name} ({scope} sessions, new-tab default)"


def profile_names(document: Dict[str, Any]) -> Iterable[str]:
    for profile in document.get("Profiles", []):
        yield str(profile.get("Name", ""))
