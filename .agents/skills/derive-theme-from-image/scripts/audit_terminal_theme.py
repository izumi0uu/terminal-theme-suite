#!/usr/bin/env python3
"""Audit OMP and Herdr role-to-surface contrast with a weighted soft gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from check_contrast import contrast_ratio, parse_color

try:
    import tomllib
except ImportError:  # Python 3.9 and 3.10
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


DEFAULT_MATRIX = (
    Path(__file__).resolve().parents[1] / "references" / "terminal-role-matrix.json"
)
MISSING = object()


def nested_value(document: Dict[str, Any], path: str) -> Any:
    value: Any = document
    for component in path.split("."):
        if not isinstance(value, dict) or component not in value:
            return MISSING
        value = value[component]
    return value


def normalized_color(value: Any) -> Optional[Tuple[str, Tuple[int, int, int]]]:
    if not isinstance(value, str):
        return None
    try:
        return parse_color(value)
    except argparse.ArgumentTypeError:
        return None


def expected_roles(specification: Dict[str, Any]) -> set[str]:
    roles = set(specification.get("surface_roles", []))
    for group in specification.get("role_groups", {}).values():
        roles.update(group)
    for rule in specification.get("rules", []):
        roles.update(rule.get("roles", []))
    return roles


def rule_roles(rule: Dict[str, Any], specification: Dict[str, Any]) -> List[str]:
    if "roles" in rule:
        return list(rule["roles"])
    return list(specification["role_groups"][rule["group"]])


def resolve_surfaces(
    document: Dict[str, Any],
    specification: Dict[str, Any],
    terminal_background: Optional[str],
) -> Tuple[Dict[str, Optional[Tuple[str, Tuple[int, int, int]]]], Dict[str, Any]]:
    resolved = {}
    raw_values = {}
    for name, surface in specification["surfaces"].items():
        raw = nested_value(document, surface["path"])
        raw_values[name] = None if raw is MISSING else raw
        color = normalized_color(raw)
        if color is None and surface.get("fallback") == "terminal-background":
            color = normalized_color(terminal_background)
        resolved[name] = color
    return resolved, raw_values


def structural_penalties(
    unknown: Iterable[str], weight: float = 1.0
) -> List[Dict[str, Any]]:
    return [
        {
            "role": role,
            "surface": None,
            "kind": "unknown-role",
            "foreground": None,
            "background": None,
            "ratio": None,
            "min_ratio": None,
            "weight": weight,
            "status": "unknown",
        }
        for role in sorted(unknown)
    ]


def audit_target(
    target: str,
    document: Dict[str, Any],
    specification: Dict[str, Any],
    terminal_background: Optional[str],
    min_score: float,
    strict: bool,
) -> Dict[str, Any]:
    role_values = nested_value(document, specification["roles_path"])
    if not isinstance(role_values, dict):
        role_values = {}

    expected = expected_roles(specification)
    actual = set(role_values)
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)
    surfaces, raw_surfaces = resolve_surfaces(
        document, specification, terminal_background
    )

    checks: List[Dict[str, Any]] = []
    for rule in specification["rules"]:
        weight = float(rule.get("weight", 1))
        for role in rule_roles(rule, specification):
            foreground = normalized_color(role_values.get(role))
            for surface_name in rule["surfaces"]:
                background = surfaces.get(surface_name)
                status = "pass"
                ratio = None
                if foreground is None:
                    status = "missing" if role not in role_values else "invalid"
                elif background is None:
                    status = "unresolved"
                else:
                    ratio = contrast_ratio(foreground[1], background[1])
                    if ratio < float(rule["min_ratio"]):
                        status = "fail"
                checks.append(
                    {
                        "role": role,
                        "surface": surface_name,
                        "kind": rule["kind"],
                        "foreground": foreground[0]
                        if foreground
                        else role_values.get(role),
                        "background": background[0]
                        if background
                        else raw_surfaces.get(surface_name),
                        "ratio": round(ratio, 2) if ratio is not None else None,
                        "min_ratio": float(rule["min_ratio"]),
                        "weight": weight,
                        "status": status,
                    }
                )

    checks.extend(structural_penalties(unknown))
    total_weight = sum(float(check["weight"]) for check in checks)
    passed_weight = sum(
        float(check["weight"]) for check in checks if check["status"] == "pass"
    )
    score = 100 * passed_weight / total_weight if total_weight else 0.0
    counts = {
        status: sum(check["status"] == status for check in checks)
        for status in ("pass", "fail", "missing", "invalid", "unresolved", "unknown")
    }
    structural_ok = (
        not unknown
        and not missing
        and not any(
            check["status"] in {"missing", "invalid", "unresolved", "unknown"}
            for check in checks
        )
    )
    effective_threshold = 100.0 if strict else min_score
    passed = score + 1e-9 >= effective_threshold and (not strict or structural_ok)
    return {
        "target": target,
        "score": round(score, 2),
        "min_score": effective_threshold,
        "passed": passed,
        "strict": strict,
        "counts": counts,
        "unknown_roles": unknown,
        "missing_roles": missing,
        "surfaces": {
            name: color[0] if color else raw_surfaces.get(name)
            for name, color in surfaces.items()
        },
        "checks": checks,
    }


def load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected an object in {path}")
    return value


def load_toml(path: Path) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError(
            "TOML support requires Python 3.11+ or tomli. "
            "Run with: uv run --no-project --with tomli "
            "audit_terminal_theme.py ..."
        )
    with path.open("rb") as handle:
        value = tomllib.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a table in {path}")
    return value


def print_report(reports: Sequence[Dict[str, Any]], show_all: bool, limit: int) -> None:
    for report in reports:
        verdict = "PASS" if report["passed"] else "BELOW GATE"
        counts = report["counts"]
        print(
            f"{report['target'].upper()}: {report['score']:.2f}/100 "
            f"(gate {report['min_score']:.2f}) {verdict}"
        )
        print(
            "  "
            + ", ".join(f"{name}={value}" for name, value in counts.items() if value)
        )
        if report["unknown_roles"]:
            print(f"  unknown roles: {', '.join(report['unknown_roles'])}")
        if report["missing_roles"]:
            print(f"  missing roles: {', '.join(report['missing_roles'])}")

        details = [
            check for check in report["checks"] if show_all or check["status"] != "pass"
        ]
        for check in details[:limit]:
            ratio = (
                f"{check['ratio']:.2f}:1"
                if isinstance(check["ratio"], (int, float))
                else "n/a"
            )
            minimum = (
                f"{check['min_ratio']:.2f}:1"
                if isinstance(check["min_ratio"], (int, float))
                else "n/a"
            )
            target = (
                f"{check['role']} -> {check['surface']}"
                if check["surface"]
                else check["role"]
            )
            print(
                f"  {check['status'].upper():<10} {target:<42} "
                f"{ratio:<9} target={minimum} weight={check['weight']:g}"
            )
        if len(details) > limit:
            print(f"  ... {len(details) - limit} more details; use --json")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--omp", type=Path, help="Generated OMP theme JSON")
    parser.add_argument("--herdr", type=Path, help="Herdr config TOML")
    parser.add_argument(
        "--terminal-background",
        help="Flat fallback for Herdr panel_bg=reset, such as '#1E1E2E'",
    )
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--min-score", type=float, default=85.0)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--show-all", action="store_true")
    parser.add_argument("--max-details", type=int, default=80)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.omp and not args.herdr:
        parser.error("provide --omp, --herdr, or both")
    if not 0 <= args.min_score <= 100:
        parser.error("--min-score must be between 0 and 100")
    if args.max_details < 1:
        parser.error("--max-details must be positive")
    if args.terminal_background and not normalized_color(args.terminal_background):
        parser.error("--terminal-background must be a hex color")

    try:
        matrix = load_json(args.matrix)
        reports = []
        if args.omp:
            reports.append(
                audit_target(
                    "omp",
                    load_json(args.omp),
                    matrix["omp"],
                    args.terminal_background,
                    args.min_score,
                    args.strict,
                )
            )
        if args.herdr:
            reports.append(
                audit_target(
                    "herdr",
                    load_toml(args.herdr),
                    matrix["herdr"],
                    args.terminal_background,
                    args.min_score,
                    args.strict,
                )
            )
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as error:
        parser.error(str(error))

    if args.json:
        print(
            json.dumps(
                {"passed": all(item["passed"] for item in reports), "reports": reports},
                indent=2,
            )
        )
    else:
        print_report(reports, args.show_all, args.max_details)
    return 0 if all(item["passed"] for item in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
