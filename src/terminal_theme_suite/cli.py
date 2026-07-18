from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

from . import __version__
from .adapters import iterm2, omp
from .config import (
    find_theme,
    load_config,
    update_iterm_daemon,
    update_theme_background,
    write_default_config,
)
from .models import Theme
from .paths import (
    BACKGROUND_DIR,
    CONFIG_FILE,
    HERDR_CONFIG,
    ITERM_API_DAEMON,
    ITERM_PROFILE_FILE,
    ITERM_RUNTIME_METADATA,
    OMP_ACTIVE_THEME,
    OMP_LIVE_RELOAD_EXTENSION,
)
from .service import adjacent_theme, apply, current_theme_id, sync


def _theme_rows(themes: Iterable[Theme], current: str) -> Iterable[str]:
    for theme in themes:
        marker = "*" if theme.id == current else " "
        source = theme.extra.get("background_source", "custom")
        background = (
            f"{theme.background.name} ({source})" if theme.background else source
        )
        yield (
            f"{marker} {theme.id:<14} {theme.name:<20} "
            f"iTerm/OMP/Herdr={theme.herdr_theme:<18} background={background}"
        )


def _print_result(result: object, quiet: bool) -> None:
    if quiet:
        return
    switch_result = result
    print(f"Switched to {switch_result.theme.name} ({switch_result.theme.id})")
    for message in switch_result.messages:
        print(f"  ok: {message}")
    for warning in switch_result.warnings:
        print(f"  note: {warning}")


def _choose_theme() -> Optional[str]:
    config = load_config()
    current = current_theme_id(config)
    lines = [
        f"{theme.id}\t{theme.name}\t{theme.description}" for theme in config.themes
    ]
    fzf = shutil.which("fzf")
    if fzf:
        result = subprocess.run(
            [
                fzf,
                "--height=50%",
                "--layout=reverse",
                "--border",
                f"--prompt=Theme ({current}) > ",
            ],
            input="\n".join(lines) + "\n",
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.split("\t", 1)[0]
        return None
    if not sys.stdin.isatty():
        return None
    for index, theme in enumerate(config.themes, start=1):
        print(f"{index}. {theme.name} ({theme.id})")
    try:
        selected = int(input("Select theme: ").strip())
    except (ValueError, EOFError):
        return None
    if 1 <= selected <= len(config.themes):
        return config.themes[selected - 1].id
    return None


def _copy_background(theme_id: str, source: Path, reference: bool) -> Path:
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".heic", ".webp"}:
        raise ValueError("Background must be PNG, JPEG, HEIC, or WebP")
    if reference:
        return source
    BACKGROUND_DIR.mkdir(parents=True, exist_ok=True)
    destination = BACKGROUND_DIR / f"{theme_id}{source.suffix.lower()}"
    if source != destination:
        shutil.copy2(source, destination)
    return destination


def _doctor() -> int:
    config = load_config()
    daemon = (
        Path(config.iterm_daemon).expanduser()
        if config.iterm_daemon
        else ITERM_API_DAEMON
    )
    api_result = subprocess.run(
        ["defaults", "read", "com.googlecode.iterm2", "EnableAPIServer"],
        capture_output=True,
        text=True,
        check=False,
    )
    api_enabled = api_result.returncode == 0 and api_result.stdout.strip() == "1"
    iterm_running = iterm2._iterm_is_running()
    daemon_live = iterm2.daemon_ready() if iterm_running else True
    omp_installed = bool(shutil.which("omp"))
    omp_reload_ready, omp_reload_detail = (
        omp.live_reload_status() if omp_installed else (True, "optional, OMP not found")
    )
    checks = [
        ("macOS", platform.system() == "Darwin", platform.platform()),
        ("iTerm2", Path("/Applications/iTerm.app").exists(), "/Applications/iTerm.app"),
        (
            "iTerm2 API",
            api_enabled,
            "enabled" if api_enabled else "restart after term-theme init",
        ),
        (
            "term-theme",
            bool(shutil.which("term-theme")),
            shutil.which("term-theme") or "not on PATH",
        ),
        ("API daemon", daemon.is_file(), str(daemon)),
        (
            "Python runtime",
            ITERM_RUNTIME_METADATA.is_file(),
            str(ITERM_RUNTIME_METADATA)
            if ITERM_RUNTIME_METADATA.is_file()
            else "use a shortcut once and approve iTerm2's download",
        ),
        (
            "daemon RPC",
            daemon_live,
            "ready"
            if iterm_running and daemon_live
            else (
                "starts with iTerm2"
                if not iterm_running
                else "restart iTerm2 or reinstall"
            ),
        ),
        (
            "OMP",
            omp_installed,
            shutil.which("omp") or "optional, not found",
        ),
        ("OMP live reload", omp_reload_ready, omp_reload_detail),
        (
            "Herdr",
            bool(shutil.which("herdr")),
            shutil.which("herdr") or "optional, not found",
        ),
        (
            "fzf",
            bool(shutil.which("fzf")),
            shutil.which("fzf") or "optional, not found",
        ),
        ("config", CONFIG_FILE.exists(), str(CONFIG_FILE)),
        ("profiles", ITERM_PROFILE_FILE.exists(), str(ITERM_PROFILE_FILE)),
        ("OMP theme", OMP_ACTIVE_THEME.exists(), str(OMP_ACTIVE_THEME)),
        ("Herdr config", HERDR_CONFIG.exists(), str(HERDR_CONFIG)),
    ]
    for name, passed, detail in checks:
        print(f"{'ok' if passed else '--':>2}  {name:<14} {detail}")
    missing_backgrounds = [
        f"{theme.id}: {theme.background}"
        for theme in config.themes
        if theme.background and not theme.background.exists()
    ]
    for item in missing_backgrounds:
        print(f"!!  missing background {item}")
    required_ok = (
        all(checks[index][1] for index in range(7)) and not missing_backgrounds
    )
    return 0 if required_ok else 1


def _add_switch_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print output (for iTerm2 shortcuts)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show the target without changing files"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="term-theme",
        description="Switch iTerm2, OMP, Herdr, and wallpaper as one theme suite.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init", help="Create config and iTerm2 dynamic profiles"
    )
    init_parser.add_argument(
        "--apply", action="store_true", help="Apply the initial/current theme"
    )
    init_parser.add_argument(
        "--daemon", type=Path, help="Path to the iTerm2 AutoLaunch API daemon"
    )

    list_parser = subparsers.add_parser("list", help="List configured theme suites")
    list_parser.add_argument(
        "--json", action="store_true", help="Print machine-readable JSON"
    )

    use_parser = subparsers.add_parser("use", help="Switch to a named theme suite")
    use_parser.add_argument("theme")
    _add_switch_options(use_parser)

    next_parser = subparsers.add_parser("next", help="Switch to the next theme suite")
    _add_switch_options(next_parser)
    previous_parser = subparsers.add_parser(
        "previous", help="Switch to the previous theme suite"
    )
    _add_switch_options(previous_parser)

    subparsers.add_parser("current", help="Print the current theme suite")
    subparsers.add_parser("choose", help="Choose a theme suite with fzf")
    subparsers.add_parser("sync", help="Regenerate iTerm2 profiles without switching")
    subparsers.add_parser("doctor", help="Check integrations and local configuration")

    background = subparsers.add_parser("background", help="Manage theme wallpapers")
    background_sub = background.add_subparsers(dest="background_command", required=True)
    background_set = background_sub.add_parser("set", help="Set a theme wallpaper")
    background_set.add_argument("theme")
    background_set.add_argument("path", type=Path)
    background_set.add_argument(
        "--reference",
        action="store_true",
        help="Reference the original file instead of copying it",
    )
    background_clear = background_sub.add_parser(
        "clear", help="Disable a theme wallpaper"
    )
    background_clear.add_argument("theme")
    background_reset = background_sub.add_parser(
        "reset", help="Restore the bundled theme wallpaper"
    )
    background_reset.add_argument("theme")

    omp_reload = subparsers.add_parser(
        "omp-live-reload", help="Manage live theme reload support for OMP"
    )
    omp_reload.add_argument("action", choices=("install", "remove", "status"))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command
    try:
        if command is None:
            if sys.stdin.isatty() and sys.stdout.isatty():
                selected = _choose_theme()
                if selected:
                    _print_result(apply(selected), quiet=False)
                    return 0
            command = "list"

        if command == "init":
            iterm2.enable_api()
            path = write_default_config()
            if args.daemon:
                update_iterm_daemon(args.daemon)
            profile_path = sync()
            print(f"Config: {path}")
            print(f"Profiles: {profile_path}")
            print(
                "Shortcuts: Control+Option+T (next), Control+Option+Shift+T (previous)"
            )
            print(
                "iTerm2 API enabled: restart once, then approve its Python Runtime "
                "download if prompted"
            )
            if args.apply:
                _print_result(apply(current_theme_id()), quiet=False)
            return 0

        if command == "list":
            config = load_config()
            current = current_theme_id(config)
            if args.json:
                print(
                    json.dumps(
                        [
                            {
                                "id": theme.id,
                                "name": theme.name,
                                "description": theme.description,
                                "background": str(theme.background)
                                if theme.background
                                else None,
                                "background_source": theme.extra.get(
                                    "background_source"
                                ),
                                "current": theme.id == current,
                            }
                            for theme in config.themes
                        ],
                        indent=2,
                    )
                )
            else:
                print("\n".join(_theme_rows(config.themes, current)))
            return 0

        if command == "use":
            _print_result(apply(args.theme, dry_run=args.dry_run), args.quiet)
            return 0

        if command in {"next", "previous"}:
            direction = 1 if command == "next" else -1
            target = adjacent_theme(direction)
            _print_result(apply(target.id, dry_run=args.dry_run), args.quiet)
            return 0

        if command == "current":
            config = load_config()
            theme = find_theme(config, current_theme_id(config))
            print(f"{theme.id}\t{theme.name}")
            return 0

        if command == "choose":
            selected = _choose_theme()
            if selected:
                _print_result(apply(selected), quiet=False)
                return 0
            return 130

        if command == "sync":
            print(sync())
            return 0

        if command == "doctor":
            return _doctor()

        if command == "omp-live-reload":
            if args.action == "install":
                added = omp.install_live_reload_extension()
                print(f"OMP live reload -> {OMP_LIVE_RELOAD_EXTENSION}")
                if added:
                    print("Restart currently running OMP processes once")
                return 0
            if args.action == "remove":
                removed = omp.remove_live_reload_extension()
                print("OMP live reload removed" if removed else "OMP live reload not installed")
                return 0
            ready, detail = omp.live_reload_status()
            print(f"{'ready' if ready else 'not ready'}\t{detail}")
            return 0 if ready else 1

        if command == "background":
            config = load_config()
            theme = find_theme(config, args.theme)
            if args.background_command == "set":
                destination = _copy_background(theme.id, args.path, args.reference)
                update_theme_background(theme.id, destination)
                print(f"{theme.id} background -> {destination}")
            elif args.background_command == "clear":
                update_theme_background(theme.id, False)
                print(f"{theme.id} background disabled")
            else:
                update_theme_background(theme.id, None)
                print(f"{theme.id} background reset to bundled preset")
            print(sync())
            return 0
    except (KeyError, ValueError, FileNotFoundError, RuntimeError) as error:
        if not getattr(args, "quiet", False):
            print(f"term-theme: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
