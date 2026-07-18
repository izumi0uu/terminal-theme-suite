from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
import fcntl
import shutil
from time import perf_counter_ns
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from .adapters import herdr, iterm2, omp
from .config import find_theme, load_config
from .io import atomic_write_json, read_json
from .models import Theme, UserConfig
from .paths import (
    BACKUP_DIR,
    HERDR_CONFIG,
    ITERM_PROFILE_FILE,
    OMP_ACTIVE_THEME,
    OMP_DIR,
    STATE_FILE,
    SWITCH_LOCK,
)


@dataclass
class SwitchResult:
    theme: Theme
    messages: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timings: Dict[str, float] = field(default_factory=dict)


@dataclass
class _StageOutcome:
    value: Optional[Tuple[str, Optional[str]]] = None
    error: Optional[Exception] = None
    duration_ms: float = 0.0


@contextmanager
def _switch_lock() -> Iterator[float]:
    SWITCH_LOCK.parent.mkdir(parents=True, exist_ok=True)
    started = perf_counter_ns()
    with SWITCH_LOCK.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        wait_ms = (perf_counter_ns() - started) / 1_000_000
        try:
            yield wait_ms
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _timed_stage(
    action: Callable[[], Tuple[str, Optional[str]]],
) -> _StageOutcome:
    started = perf_counter_ns()
    try:
        return _StageOutcome(
            value=action(),
            duration_ms=(perf_counter_ns() - started) / 1_000_000,
        )
    except Exception as error:
        return _StageOutcome(
            error=error,
            duration_ms=(perf_counter_ns() - started) / 1_000_000,
        )


def _backup_once() -> List[str]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    sources = (
        (OMP_DIR / "config.yml", "omp-config.yml"),
        (OMP_ACTIVE_THEME, "omp-active-theme.json"),
        (HERDR_CONFIG, "herdr-config.toml"),
    )
    created = []
    for source, name in sources:
        destination = BACKUP_DIR / name
        if source.exists() and not destination.exists():
            shutil.copy2(source, destination)
            created.append(str(destination))
    return created


def current_theme_id(config: Optional[UserConfig] = None) -> str:
    config = config or load_config()
    state = read_json(STATE_FILE, {}) or {}
    value = state.get("theme")
    if value and any(theme.id == value for theme in config.themes):
        return str(value)
    return config.themes[0].id


def adjacent_theme(direction: int, config: Optional[UserConfig] = None) -> Theme:
    config = config or load_config()
    current = current_theme_id(config)
    ids = [theme.id for theme in config.themes]
    index = ids.index(current) if current in ids else 0
    return config.themes[(index + direction) % len(config.themes)]


def sync(active_theme_id: Optional[str] = None) -> str:
    config = load_config()
    active = active_theme_id or current_theme_id(config)
    return str(iterm2.sync_profiles(config, active))


def configure_omp(theme_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
    with _switch_lock():
        config = load_config()
        theme = find_theme(config, theme_id or current_theme_id(config))
        _backup_once()
        return omp.configure_theme(theme)


def _apply_locked(
    config: UserConfig,
    theme: Theme,
    result: SwitchResult,
    total_started: int,
    dry_run: bool,
) -> SwitchResult:
    if dry_run:
        result.messages.append(f"Would switch to {theme.id}")
        result.timings["total"] = (perf_counter_ns() - total_started) / 1_000_000
        return result

    started = perf_counter_ns()
    for backup in _backup_once():
        result.messages.append(f"Backup -> {backup}")
    result.timings["backup"] = (perf_counter_ns() - started) / 1_000_000

    started = perf_counter_ns()
    if ITERM_PROFILE_FILE.exists():
        result.messages.append(f"Profiles -> {ITERM_PROFILE_FILE}")
    else:
        result.messages.append(f"Profiles -> {iterm2.sync_profiles(config, theme.id)}")
    result.timings["profiles"] = (perf_counter_ns() - started) / 1_000_000

    actions = {
        "iterm2": lambda: (
            iterm2.apply_profile(
                theme.profile_name, iterm2.theme_profile_guid(theme), config.scope
            ),
            None,
        ),
        "omp": lambda: omp.apply_theme(theme),
        "herdr": lambda: herdr.apply_theme(theme),
    }
    started = perf_counter_ns()
    with ThreadPoolExecutor(max_workers=len(actions)) as executor:
        futures = {
            name: executor.submit(_timed_stage, action)
            for name, action in actions.items()
        }
        outcomes = {name: future.result() for name, future in futures.items()}
    result.timings["integrations"] = (perf_counter_ns() - started) / 1_000_000
    for name, outcome in outcomes.items():
        result.timings[name] = outcome.duration_ms

    errors = []
    for name, label in (("iterm2", "iTerm2"), ("omp", "OMP"), ("herdr", "Herdr")):
        outcome = outcomes[name]
        if outcome.error:
            errors.append(f"{label}: {outcome.error}")
            continue
        if outcome.value is None:
            errors.append(f"{label}: integration returned no result")
            continue
        message, warning = outcome.value
        result.messages.append(message)
        if warning:
            result.warnings.append(warning)

    if errors:
        result.timings["total"] = (perf_counter_ns() - total_started) / 1_000_000
        raise RuntimeError(
            "Theme switch incomplete; state was not updated: " + "; ".join(errors)
        )

    started = perf_counter_ns()
    atomic_write_json(
        STATE_FILE,
        {
            "theme": theme.id,
            "profile_guid": iterm2.theme_profile_guid(theme),
            "profile_name": theme.profile_name,
            "scope": config.scope,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    result.timings["state"] = (perf_counter_ns() - started) / 1_000_000
    result.timings["total"] = (perf_counter_ns() - total_started) / 1_000_000
    return result


def apply(theme_id: str, dry_run: bool = False) -> SwitchResult:
    total_started = perf_counter_ns()
    with _switch_lock() as lock_wait:
        started = perf_counter_ns()
        config = load_config()
        theme = find_theme(config, theme_id)
        result = SwitchResult(theme=theme)
        result.timings["lock_wait"] = lock_wait
        result.timings["config"] = (perf_counter_ns() - started) / 1_000_000
        return _apply_locked(config, theme, result, total_started, dry_run)


def apply_adjacent(direction: int, dry_run: bool = False) -> SwitchResult:
    total_started = perf_counter_ns()
    with _switch_lock() as lock_wait:
        started = perf_counter_ns()
        config = load_config()
        theme = adjacent_theme(direction, config)
        result = SwitchResult(theme=theme)
        result.timings["lock_wait"] = lock_wait
        result.timings["config"] = (perf_counter_ns() - started) / 1_000_000
        return _apply_locked(config, theme, result, total_started, dry_run)
