#!/usr/bin/env python3
"""Extract raw image colors and layout complexity without modifying the image."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

try:
    from PIL import Image, ImageFilter, ImageOps, ImageStat
except ImportError as error:
    raise SystemExit(
        "Pillow is required. Run in an isolated environment, for example: "
        "uv run --with pillow extract_palette.py IMAGE"
    ) from error


REGION_NAMES = (
    "top-left",
    "top-center",
    "top-right",
    "middle-left",
    "middle-center",
    "middle-right",
    "bottom-left",
    "bottom-center",
    "bottom-right",
)


def wcag_luminance(rgb: Tuple[int, int, int]) -> float:
    channels = []
    for component in rgb:
        value = component / 255
        channels.append(
            value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def hex_color(rgb: Sequence[int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb[:3])


def quantized_palette(image: Image.Image, count: int) -> List[Dict[str, object]]:
    quantized = image.quantize(colors=count, method=Image.Quantize.MEDIANCUT)
    palette = quantized.getpalette() or []
    histogram = quantized.getcolors(maxcolors=count) or []
    total = sum(coverage for coverage, _ in histogram) or 1
    rows = []
    for coverage, index in sorted(histogram, reverse=True):
        rgb = tuple(palette[index * 3 : index * 3 + 3])
        rows.append(
            {
                "hex": hex_color(rgb),
                "coverage": round(coverage / total * 100, 2),
                "luminance": round(wcag_luminance(rgb), 4),
            }
        )
    return rows


def region_complexity(image: Image.Image) -> Tuple[str, List[Dict[str, object]]]:
    edges = ImageOps.grayscale(image).filter(ImageFilter.FIND_EDGES)
    width, height = edges.size
    rows = []
    for row in range(3):
        for column in range(3):
            box = (
                column * width // 3,
                row * height // 3,
                (column + 1) * width // 3,
                (row + 1) * height // 3,
            )
            score = ImageStat.Stat(edges.crop(box)).mean[0]
            rows.append(
                {
                    "region": REGION_NAMES[row * 3 + column],
                    "edge_score": round(score, 2),
                }
            )
    quietest = min(rows, key=lambda item: float(item["edge_score"]))["region"]
    return str(quietest), rows


def complexity_label(score: float) -> str:
    if score < 7:
        return "low"
    if score < 16:
        return "medium"
    return "high"


def load_sample(path: Path, sample_size: int) -> Tuple[Image.Image, Dict[str, object]]:
    with Image.open(path) as source:
        source = ImageOps.exif_transpose(source)
        original_size = source.size
        image = source.convert("RGB")
    image.thumbnail((sample_size, sample_size), Image.Resampling.LANCZOS)
    gray = ImageOps.grayscale(image)
    luminance = ImageStat.Stat(gray)
    quietest, regions = region_complexity(image)
    edge_mean = sum(float(item["edge_score"]) for item in regions) / len(regions)
    metadata = {
        "path": str(path.resolve()),
        "width": original_size[0],
        "height": original_size[1],
        "aspect_ratio": round(original_size[0] / original_size[1], 3),
        "mean_brightness": round(luminance.mean[0], 2),
        "brightness_stddev": round(luminance.stddev[0], 2),
        "complexity": complexity_label(edge_mean),
        "edge_score": round(edge_mean, 2),
        "quietest_region": quietest,
        "regions": regions,
    }
    return image, metadata


def combined_sample(images: Iterable[Image.Image], sample_size: int) -> Image.Image:
    items = list(images)
    pixels = []
    for image in items:
        if hasattr(image, "get_flattened_data"):
            pixels.extend(image.get_flattened_data())
        else:
            pixels.extend(image.getdata())
    width = sample_size
    height = math.ceil(len(pixels) / width)
    pixels.extend([pixels[-1]] * (width * height - len(pixels)))
    canvas = Image.new("RGB", (width, height))
    canvas.putdata(pixels)
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--colors", type=int, default=10)
    parser.add_argument("--sample-size", type=int, default=384)
    parser.add_argument("--json", action="store_true", help="Print JSON")
    args = parser.parse_args()

    if not 2 <= args.colors <= 32:
        parser.error("--colors must be between 2 and 32")
    if not 64 <= args.sample_size <= 1024:
        parser.error("--sample-size must be between 64 and 1024")
    missing = [path for path in args.images if not path.is_file()]
    if missing:
        parser.error(f"image not found: {missing[0]}")

    samples = []
    reports = []
    for path in args.images:
        image, metadata = load_sample(path, args.sample_size)
        samples.append(image)
        metadata["palette"] = quantized_palette(image, args.colors)
        reports.append(metadata)

    combined = quantized_palette(
        combined_sample(samples, args.sample_size), args.colors
    )
    document = {"images": reports, "combined_palette": combined}
    if args.json:
        print(json.dumps(document, indent=2))
        return 0

    for report in reports:
        print(f"\n## {report['path']}")
        print(
            f"size={report['width']}x{report['height']} "
            f"aspect={report['aspect_ratio']} brightness={report['mean_brightness']} "
            f"complexity={report['complexity']} quietest={report['quietest_region']}"
        )
        print("color       coverage  luminance")
        for color in report["palette"]:
            print(
                f"{color['hex']:<11} {color['coverage']:>7.2f}%  "
                f"{color['luminance']:.4f}"
            )
    if len(reports) > 1:
        print("\n## Combined palette")
        for color in combined:
            print(f"{color['hex']:<11} {color['coverage']:>7.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
