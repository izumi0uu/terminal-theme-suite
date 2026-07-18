#!/usr/bin/env python3
"""Sample text contrast over a rendered wallpaper with a soft coverage gate."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

from check_contrast import contrast_ratio, parse_color

try:
    from PIL import Image, ImageOps
except ImportError as error:  # pragma: no cover - exercised by the CLI dependency check
    raise SystemExit(
        "Pillow is required. Run with: uv run --no-project --with pillow "
        "sample_wallpaper_contrast.py ..."
    ) from error


RGB = Tuple[int, int, int]
Viewport = Tuple[int, int]

ANCHORS = {
    "top-left": (0.0, 0.0),
    "top": (0.5, 0.0),
    "top-right": (1.0, 0.0),
    "left": (0.0, 0.5),
    "center": (0.5, 0.5),
    "right": (1.0, 0.5),
    "bottom-left": (0.0, 1.0),
    "bottom": (0.5, 1.0),
    "bottom-right": (1.0, 1.0),
}


def viewport_value(value: str) -> Viewport:
    try:
        width_text, height_text = value.lower().split("x", 1)
        width, height = int(width_text), int(height_text)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError(
            f"invalid viewport {value!r}; expected WIDTHxHEIGHT"
        ) from error
    if width < 1 or height < 1:
        raise argparse.ArgumentTypeError("viewport dimensions must be positive")
    return width, height


def foreground_value(value: str) -> Dict[str, Any]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(
            f"invalid foreground {value!r}; expected ROLE=#RRGGBB[:RATIO]"
        )
    role, color_and_ratio = value.split("=", 1)
    role = role.strip()
    if not role:
        raise argparse.ArgumentTypeError("foreground role cannot be empty")

    parts = color_and_ratio.rsplit(":", 1)
    color_text = parts[0]
    try:
        ratio = float(parts[1]) if len(parts) == 2 else 4.5
        color, rgb = parse_color(color_text)
    except (ValueError, argparse.ArgumentTypeError) as error:
        raise argparse.ArgumentTypeError(
            f"invalid foreground {value!r}; expected ROLE=#RRGGBB[:RATIO]"
        ) from error
    if not math.isfinite(ratio) or ratio < 1 or ratio > 21:
        raise argparse.ArgumentTypeError("foreground ratio must be between 1 and 21")
    return {"role": role, "color": color, "rgb": rgb, "min_ratio": ratio}


def scaled_size(source: Viewport, viewport: Viewport, mode: str) -> Viewport:
    source_width, source_height = source
    viewport_width, viewport_height = viewport
    if mode == "stretch":
        return viewport
    scales = (
        viewport_width / source_width,
        viewport_height / source_height,
    )
    scale = max(scales) if mode == "fill" else min(scales)
    return (
        max(1, round(source_width * scale)),
        max(1, round(source_height * scale)),
    )


def render_wallpaper(
    image: Image.Image,
    viewport: Viewport,
    background: RGB,
    blend: float,
    mode: str,
    anchor: str,
) -> Tuple[Image.Image, Dict[str, Any]]:
    source = ImageOps.exif_transpose(image).convert("RGBA")
    resized_size = scaled_size(source.size, viewport, mode)
    resized = source.resize(resized_size, Image.Resampling.LANCZOS)
    x_factor, y_factor = ANCHORS[anchor]
    viewport_width, viewport_height = viewport
    resized_width, resized_height = resized_size

    if mode == "fill":
        crop_x = round(max(0, resized_width - viewport_width) * x_factor)
        crop_y = round(max(0, resized_height - viewport_height) * y_factor)
        crop_box = (
            crop_x,
            crop_y,
            crop_x + viewport_width,
            crop_y + viewport_height,
        )
        positioned = resized.crop(crop_box)
        offset = (-crop_x, -crop_y)
    else:
        crop_box = None
        offset = (
            round(max(0, viewport_width - resized_width) * x_factor),
            round(max(0, viewport_height - resized_height) * y_factor),
        )
        positioned = Image.new("RGBA", viewport, (*background, 255))
        positioned.alpha_composite(resized, dest=offset)

    solid = Image.new("RGB", viewport, background)
    wallpaper = Image.alpha_composite(
        Image.new("RGBA", viewport, (*background, 255)), positioned
    ).convert("RGB")
    rendered = Image.blend(wallpaper, solid, blend)
    geometry = {
        "source_size": list(source.size),
        "resized_size": list(resized_size),
        "offset": list(offset),
        "crop_box": list(crop_box) if crop_box else None,
    }
    return rendered, geometry


def percentile(sorted_values: Sequence[float], fraction: float) -> float:
    if not sorted_values:
        raise ValueError("cannot calculate a percentile without samples")
    position = (len(sorted_values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    remainder = position - lower
    return sorted_values[lower] * (1 - remainder) + sorted_values[upper] * remainder


def worst_region(
    rows: Sequence[Sequence[float]], width: int, height: int
) -> Dict[str, Any]:
    region_width = min(3, width)
    region_height = min(3, height)
    horizontal: List[List[float]] = []
    for row in rows:
        running = sum(row[:region_width])
        sums = [running]
        for x in range(region_width, width):
            running += row[x] - row[x - region_width]
            sums.append(running)
        horizontal.append(sums)

    best_sum = math.inf
    best_x = 0
    best_y = 0
    for x in range(len(horizontal[0])):
        running = sum(horizontal[y][x] for y in range(region_height))
        if running < best_sum:
            best_sum, best_x, best_y = running, x, 0
        for y in range(region_height, height):
            running += horizontal[y][x] - horizontal[y - region_height][x]
            if running < best_sum:
                best_sum, best_x, best_y = running, x, y - region_height + 1

    region_values = [
        rows[y][x]
        for y in range(best_y, best_y + region_height)
        for x in range(best_x, best_x + region_width)
    ]
    return {
        "x": best_x,
        "y": best_y,
        "width": region_width,
        "height": region_height,
        "mean_ratio": round(best_sum / len(region_values), 2),
        "min_ratio": round(min(region_values), 2),
        "max_ratio": round(max(region_values), 2),
    }


def audit_foreground(
    rendered: Image.Image,
    foreground: Dict[str, Any],
    min_pass_coverage: float,
    strict: bool,
) -> Dict[str, Any]:
    width, height = rendered.size
    pixels = rendered.load()
    rows: List[List[float]] = []
    values: List[float] = []
    passing = 0
    minimum = math.inf
    minimum_at = (0, 0)
    threshold = foreground["min_ratio"]

    for y in range(height):
        row: List[float] = []
        for x in range(width):
            ratio = contrast_ratio(foreground["rgb"], pixels[x, y])
            row.append(ratio)
            values.append(ratio)
            if ratio >= threshold:
                passing += 1
            if ratio < minimum:
                minimum = ratio
                minimum_at = (x, y)
        rows.append(row)

    values.sort()
    coverage = 100 * passing / len(values)
    effective_coverage = 100.0 if strict else min_pass_coverage
    passed = coverage + 1e-9 >= effective_coverage
    warnings = []
    if minimum < threshold:
        warnings.append("minimum-below-target")
    if percentile(values, 0.01) < threshold:
        warnings.append("p01-below-target")
    if percentile(values, 0.05) < threshold:
        warnings.append("p05-below-target")

    return {
        "role": foreground["role"],
        "foreground": foreground["color"],
        "min_ratio_target": threshold,
        "coverage_percent": round(coverage, 2),
        "min_pass_coverage": effective_coverage,
        "passed": passed,
        "strict": strict,
        "sample_count": len(values),
        "statistics": {
            "minimum": round(minimum, 2),
            "minimum_at": list(minimum_at),
            "p01": round(percentile(values, 0.01), 2),
            "p05": round(percentile(values, 0.05), 2),
            "median": round(percentile(values, 0.5), 2),
        },
        "worst_3x3_region": worst_region(rows, width, height),
        "warnings": warnings,
    }


def audit_viewport(
    image: Image.Image,
    viewport: Viewport,
    foregrounds: Sequence[Dict[str, Any]],
    background: Tuple[str, RGB],
    blend: float,
    mode: str,
    anchor: str,
    min_pass_coverage: float,
    strict: bool,
) -> Dict[str, Any]:
    rendered, geometry = render_wallpaper(
        image, viewport, background[1], blend, mode, anchor
    )
    roles = [
        audit_foreground(rendered, foreground, min_pass_coverage, strict)
        for foreground in foregrounds
    ]
    return {
        "viewport": list(viewport),
        "background": background[0],
        "blend": blend,
        "mode": mode,
        "anchor": anchor,
        "geometry": geometry,
        "passed": all(role["passed"] for role in roles),
        "roles": roles,
    }


def print_report(report: Dict[str, Any]) -> None:
    verdict = "PASS" if report["passed"] else "BELOW GATE"
    print(f"WALLPAPER: {verdict} {report['image']}")
    for viewport in report["viewports"]:
        width, height = viewport["viewport"]
        print(
            f"  {width}x{height} {viewport['mode']}/{viewport['anchor']} "
            f"blend={viewport['blend']:.2f}"
        )
        for role in viewport["roles"]:
            role_verdict = "PASS" if role["passed"] else "BELOW GATE"
            stats = role["statistics"]
            region = role["worst_3x3_region"]
            print(
                f"    {role['role']}: coverage={role['coverage_percent']:.2f}% "
                f"(gate {role['min_pass_coverage']:.2f}%) {role_verdict}"
            )
            print(
                f"      min={stats['minimum']:.2f}:1 at "
                f"({stats['minimum_at'][0]},{stats['minimum_at'][1]}) "
                f"p01={stats['p01']:.2f}:1 p05={stats['p05']:.2f}:1 "
                f"median={stats['median']:.2f}:1 target={role['min_ratio_target']:.2f}:1"
            )
            print(
                f"      worst 3x3=({region['x']},{region['y']}) "
                f"mean={region['mean_ratio']:.2f}:1 "
                f"range={region['min_ratio']:.2f}-{region['max_ratio']:.2f}:1"
            )
            if role["warnings"]:
                print(f"      warnings: {', '.join(role['warnings'])}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument(
        "--background", required=True, help="Solid background hex color"
    )
    parser.add_argument(
        "--blend",
        type=float,
        default=0.0,
        help="Solid background fraction: 0=image only, 1=solid only",
    )
    parser.add_argument("--mode", choices=("fill", "fit", "stretch"), default="fill")
    parser.add_argument("--anchor", choices=tuple(ANCHORS), default="center")
    parser.add_argument(
        "--viewport",
        action="append",
        type=viewport_value,
        required=True,
        help="Rendered WIDTHxHEIGHT; repeat for multiple viewports",
    )
    parser.add_argument(
        "--foreground",
        action="append",
        type=foreground_value,
        required=True,
        help="ROLE=#RRGGBB[:RATIO]; repeat for multiple roles",
    )
    parser.add_argument("--min-pass-coverage", type=float, default=90.0)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not math.isfinite(args.blend) or not 0 <= args.blend <= 1:
        parser.error("--blend must be between 0 and 1")
    if (
        not math.isfinite(args.min_pass_coverage)
        or not 0 <= args.min_pass_coverage <= 100
    ):
        parser.error("--min-pass-coverage must be between 0 and 100")
    try:
        background = parse_color(args.background)
        with Image.open(args.image) as image:
            viewports = [
                audit_viewport(
                    image,
                    viewport,
                    args.foreground,
                    background,
                    args.blend,
                    args.mode,
                    args.anchor,
                    args.min_pass_coverage,
                    args.strict,
                )
                for viewport in args.viewport
            ]
    except (OSError, ValueError, argparse.ArgumentTypeError) as error:
        parser.error(str(error))

    report = {
        "image": str(args.image),
        "passed": all(viewport["passed"] for viewport in viewports),
        "strict": args.strict,
        "viewports": viewports,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
