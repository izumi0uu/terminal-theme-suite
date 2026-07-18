#!/usr/bin/env python3
"""Report WCAG contrast ratios for one background and multiple foregrounds."""

from __future__ import annotations

import argparse
import json
import re
from typing import Dict, List, Tuple


HEX_COLOR = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def parse_color(value: str) -> Tuple[str, Tuple[int, int, int]]:
    match = HEX_COLOR.fullmatch(value.strip())
    if not match:
        raise argparse.ArgumentTypeError(f"invalid hex color: {value!r}")
    raw = match.group(1)
    if len(raw) == 3:
        raw = "".join(character * 2 for character in raw)
    rgb = tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))
    return f"#{raw.upper()}", rgb


def relative_luminance(rgb: Tuple[int, int, int]) -> float:
    channels = []
    for component in rgb:
        value = component / 255
        channels.append(
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(first: Tuple[int, int, int], second: Tuple[int, int, int]) -> float:
    lighter, darker = sorted(
        (relative_luminance(first), relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def result(background: str, foreground: str) -> Dict[str, object]:
    normalized_background, background_rgb = parse_color(background)
    normalized_foreground, foreground_rgb = parse_color(foreground)
    ratio = contrast_ratio(background_rgb, foreground_rgb)
    return {
        "background": normalized_background,
        "foreground": normalized_foreground,
        "ratio": round(ratio, 2),
        "aa_normal": ratio >= 4.5,
        "aa_large": ratio >= 3.0,
        "aaa_normal": ratio >= 7.0,
        "aaa_large": ratio >= 4.5,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--background", required=True, help="Background hex color")
    parser.add_argument(
        "--foreground",
        action="append",
        required=True,
        help="Foreground hex color; repeat for multiple colors",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    try:
        rows: List[Dict[str, object]] = [
            result(args.background, foreground) for foreground in args.foreground
        ]
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))

    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    print("background  foreground  ratio   AA text  AA large  AAA text")
    for row in rows:
        print(
            f"{row['background']:<11} {row['foreground']:<11} "
            f"{row['ratio']:>5.2f}:1  "
            f"{'pass' if row['aa_normal'] else 'fail':<7}  "
            f"{'pass' if row['aa_large'] else 'fail':<8}  "
            f"{'pass' if row['aaa_normal'] else 'fail'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
