from __future__ import annotations

from datetime import datetime
import hashlib
import json
from importlib import resources
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

from ..io import atomic_write_json, atomic_write_text
from ..models import Theme
from ..paths import (
    OMP_ACTIVE_THEME,
    OMP_GENERATION_FILE,
    OMP_LIVE_RELOAD_EXTENSION,
    OMP_RUNTIME_DIR,
)


OMP_THEME_SCHEMA = (
    "https://raw.githubusercontent.com/can1357/oh-my-pi/main/"
    "packages/coding-agent/src/modes/theme/theme-schema.json"
)
OMP_ACK_TIMEOUT_SECONDS = 1.0
OMP_ACK_POLL_SECONDS = 0.04
OMP_START_TIME_TOLERANCE_SECONDS = 3.0


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
    """Install the OMP startup hook. Return True when running OMP must reload it."""
    executable = executable or shutil.which("omp")
    if not executable:
        return False
    source = _extension_source()
    source_changed = (
        not OMP_LIVE_RELOAD_EXTENSION.exists()
        or OMP_LIVE_RELOAD_EXTENSION.read_text(encoding="utf-8") != source
    )
    if source_changed:
        atomic_write_text(OMP_LIVE_RELOAD_EXTENSION, source)
    extensions = _extensions(executable)
    if any(_same_path(item, OMP_LIVE_RELOAD_EXTENSION) for item in extensions):
        return source_changed
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


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _parse_process_time(value: str) -> Optional[float]:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def _running_omp_processes() -> Dict[int, float]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,lstart=,comm="],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}
    processes: Dict[int, float] = {}
    for line in result.stdout.splitlines():
        parts = line.split(None, 6)
        if len(parts) != 7 or Path(parts[6]).name != "omp":
            continue
        try:
            pid = int(parts[0])
            started = datetime.strptime(
                " ".join(parts[1:6]), "%a %b %d %H:%M:%S %Y"
            ).astimezone()
        except ValueError:
            continue
        processes[pid] = started.timestamp()
    return processes


def _runtime_states(
    processes: Optional[Dict[int, float]] = None,
) -> Dict[int, Dict[str, Any]]:
    processes = processes if processes is not None else _running_omp_processes()
    states: Dict[int, Dict[str, Any]] = {}
    if not OMP_RUNTIME_DIR.is_dir():
        return states
    for path in OMP_RUNTIME_DIR.glob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            pid = int(value["pid"])
            process_started_at = _parse_process_time(value["process_started_at"])
            token = value["token"]
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
        if (
            isinstance(token, str)
            and bool(token)
            and process_started_at is not None
            and pid in processes
            and _pid_running(pid)
            and abs(processes[pid] - process_started_at)
            <= OMP_START_TIME_TOLERANCE_SECONDS
            and value.get("theme") == "terminal-theme-suite"
        ):
            states[pid] = value
    return states


def _read_generation() -> Optional[Dict[str, str]]:
    try:
        value = json.loads(OMP_GENERATION_FILE.read_text(encoding="utf-8"))
        generation = value["generation"]
        theme_sha256 = value["theme_sha256"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None
    if not isinstance(generation, str) or not isinstance(theme_sha256, str):
        return None
    return {"generation": generation, "theme_sha256": theme_sha256}


def _ack_matches(state: Dict[str, Any], generation: Dict[str, str]) -> bool:
    return (
        state.get("ready") is True
        and state.get("applied_generation") == generation["generation"]
        and state.get("applied_theme_sha256") == generation["theme_sha256"]
    )


def runtime_reload_status() -> Tuple[bool, str]:
    processes = _running_omp_processes()
    states = _runtime_states(processes)
    ready_pids = {pid for pid, value in states.items() if value.get("ready") is True}
    failed = {
        pid: str(value.get("error") or "theme activation failed")
        for pid, value in states.items()
        if value.get("ready") is not True
    }

    running_pids = set(processes)
    if not running_pids:
        return (
            True,
            "extension installed; no running OMP processes; applies on next start",
        )
    missing = running_pids - set(states)
    if missing:
        return False, (
            "extension installed but not loaded by OMP PID(s): "
            f"{', '.join(map(str, sorted(missing)))}; restart OMP inside Herdr once"
        )
    if failed:
        details = ", ".join(f"{pid}: {error}" for pid, error in sorted(failed.items()))
        return False, f"OMP extension loaded but theme activation failed ({details})"

    generation = _read_generation()
    if generation:
        unacknowledged = {
            pid for pid, state in states.items() if not _ack_matches(state, generation)
        }
        if unacknowledged:
            return False, (
                f"watcher active but generation {generation['generation']} was not "
                "acknowledged by OMP PID(s): "
                f"{', '.join(map(str, sorted(unacknowledged)))}"
            )
    detail = f"watcher active in OMP PID(s): {', '.join(map(str, sorted(ready_pids)))}"
    if generation:
        detail += f"; generation {generation['generation']} acknowledged"
    return True, detail


def live_reload_installation_status(
    executable: Optional[str] = None,
) -> Tuple[bool, str]:
    executable = executable or shutil.which("omp")
    if not executable:
        return False, "OMP is not installed"
    registered = any(
        _same_path(item, OMP_LIVE_RELOAD_EXTENSION) for item in _extensions(executable)
    )
    installed = OMP_LIVE_RELOAD_EXTENSION.is_file() and registered
    detail = str(OMP_LIVE_RELOAD_EXTENSION)
    return installed, detail


def live_reload_status(executable: Optional[str] = None) -> Tuple[bool, str]:
    installed, detail = live_reload_installation_status(executable)
    if not installed:
        return False, detail
    return runtime_reload_status()


def configuration_status(executable: Optional[str] = None) -> Tuple[bool, str]:
    executable = executable or shutil.which("omp")
    if not executable:
        return False, "OMP is not installed"
    installed, detail = live_reload_installation_status(executable)
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
    if not installed:
        drift.append("extensions")
    if drift:
        return False, f"run term-theme repair ({', '.join(drift)})"
    return runtime_reload_status()


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


def _write_theme(theme: Theme) -> Dict[str, str]:
    document = build_theme(theme)
    content = json.dumps(document, indent=2) + "\n"
    generation = {
        "generation": str(uuid.uuid4()),
        "theme_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "created_at": datetime.now().astimezone().isoformat(),
    }
    atomic_write_text(OMP_ACTIVE_THEME, content)
    atomic_write_json(OMP_GENERATION_FILE, generation)
    return generation


def _wait_for_generation(
    generation: Dict[str, str], timeout: Optional[float] = None
) -> Tuple[bool, str]:
    timeout = OMP_ACK_TIMEOUT_SECONDS if timeout is None else timeout
    processes = _running_omp_processes()
    target_pids = set(processes)
    generation_id = generation["generation"]
    if not target_pids:
        return False, "no running OMP processes; theme will apply on next OMP start"

    expected_tokens: Dict[int, str] = {}
    token_changed = set()
    deadline = time.monotonic() + timeout
    latest_states: Dict[int, Dict[str, Any]] = {}
    while True:
        latest_states = _runtime_states(processes)
        for pid, state in latest_states.items():
            token = str(state["token"])
            expected = expected_tokens.setdefault(pid, token)
            if token != expected:
                token_changed.add(pid)

        failed = {
            pid: str(state.get("error") or "theme activation failed")
            for pid, state in latest_states.items()
            if state.get("error_generation") == generation_id and state.get("error")
        }
        if failed:
            details = ", ".join(
                f"{pid}: {error}" for pid, error in sorted(failed.items())
            )
            return False, f"OMP rejected generation {generation_id} ({details})"

        acknowledged = {
            pid
            for pid, state in latest_states.items()
            if pid not in token_changed and _ack_matches(state, generation)
        }
        if acknowledged == target_pids:
            return True, (
                f"generation {generation_id} acknowledged by OMP PID(s): "
                f"{', '.join(map(str, sorted(acknowledged)))}"
            )
        if time.monotonic() >= deadline:
            break
        time.sleep(OMP_ACK_POLL_SECONDS)

    missing = target_pids - set(latest_states)
    if missing:
        return False, (
            "OMP extension is not loaded in PID(s): "
            f"{', '.join(map(str, sorted(missing)))}; restart OMP inside Herdr once"
        )
    if token_changed:
        return False, (
            "OMP runtime token changed while waiting for PID(s): "
            f"{', '.join(map(str, sorted(token_changed)))}"
        )
    unacknowledged = {
        pid
        for pid, state in latest_states.items()
        if not _ack_matches(state, generation)
    }
    return False, (
        f"OMP did not acknowledge generation {generation_id} within {timeout:.1f}s "
        f"(PID(s): {', '.join(map(str, sorted(unacknowledged)))})"
    )


def configure_theme(theme: Theme) -> Tuple[str, str | None]:
    generation = _write_theme(theme)
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
    if extension_added:
        warning = (
            "Live-reload extension changed; restart OMP inside Herdr once to load it "
            "(restarting iTerm2 alone does not restart persisted Herdr panes)"
        )
    else:
        runtime_ready, runtime_detail = _wait_for_generation(generation)
        warning = None if runtime_ready else runtime_detail
    return "OMP configured -> terminal-theme-suite (dark/light, Nerd Font)", warning


def apply_theme(theme: Theme) -> Tuple[str, str | None]:
    generation = _write_theme(theme)
    runtime_ready, detail = _wait_for_generation(generation)
    if runtime_ready:
        return f"OMP theme applied ({detail})", None
    return "OMP theme file updated", detail
