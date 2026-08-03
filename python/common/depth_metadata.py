"""Offline extraction and validation of a canonical depth-level list."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

from .constants import ANALYSIS_DEPTH_M, DEPTH_TOLERANCE_M


class DepthMetadataError(ValueError):
    """Raised when a depth list is missing or fails closed validation."""


def _read_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DepthMetadataError("metadata JSON must contain an object")
    return value


def extract_depth_levels(metadata: dict[str, Any]) -> tuple[float, ...]:
    """Extract depth values from a canonical snapshot or a describe response."""

    raw = metadata.get("depth_levels_m")
    if raw is None and isinstance(metadata.get("depth"), dict):
        raw = metadata["depth"].get("levels_m")
    if not isinstance(raw, list):
        raise DepthMetadataError("full depth list is absent; no depth values may be invented")
    try:
        levels = tuple(float(value) for value in raw)
    except (TypeError, ValueError) as exc:
        raise DepthMetadataError("depth list contains a non-numeric value") from exc
    if any(not math.isfinite(value) for value in levels):
        raise DepthMetadataError("depth list contains a non-finite value")
    return levels


def validate_depth_levels(
    levels: tuple[float, ...],
    *,
    expected_count: int = 50,
    target_depth_m: float = ANALYSIS_DEPTH_M,
    tolerance_m: float = DEPTH_TOLERANCE_M,
) -> None:
    """Validate count, monotonic ordering, and approved top-layer target."""

    if len(levels) != expected_count:
        raise DepthMetadataError(f"expected {expected_count} depth levels, observed {len(levels)}")
    increasing = all(left < right for left, right in zip(levels, levels[1:]))
    decreasing = all(left > right for left, right in zip(levels, levels[1:]))
    if not (increasing or decreasing):
        raise DepthMetadataError("depth levels must be strictly monotonic")
    top_depth = min(levels)
    if abs(top_depth - target_depth_m) > tolerance_m:
        raise DepthMetadataError("shallowest depth does not match approved target within tolerance")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        levels = extract_depth_levels(_read_json(args.metadata))
        validate_depth_levels(levels)
    except (OSError, json.JSONDecodeError, DepthMetadataError) as exc:
        print(f"status=BLOCKED\nerror={exc}")
        return 2
    order = "ascending" if levels[0] < levels[-1] else "descending"
    print("status=PASS_WITH_NOTES")
    print(
        f"evidence=validated_depth_count={len(levels)}; "
        f"top_depth_m={min(levels):.9f}; coordinate_order={order}"
    )
    print("limitations=Depth validation uses active sanitized metadata; no NetCDF was accessed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
