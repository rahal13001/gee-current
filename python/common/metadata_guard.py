"""Offline metadata compatibility guard for the active Copernicus baseline.

The guard compares two sanitized, canonical metadata JSON objects. It never
authenticates, contacts Copernicus, downloads data, or writes files. A missing
or changed critical field fails closed so a later pipeline cannot silently use
an incompatible dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .constants import (
    ANALYSIS_DEPTH_M,
    CURRENT_UNITS,
    CURRENT_VARIABLES,
    DAILY_DATASET_ID,
    DEPTH_TOLERANCE_M,
    MONTHLY_DATASET_ID,
    PRODUCT_ID,
    PROJECT_PERIOD_END_EXCLUSIVE,
    PROJECT_PERIOD_START,
)


@dataclass(frozen=True)
class MetadataChange:
    """One incompatible or missing metadata field."""

    path: str
    expected: Any
    observed: Any
    critical: bool = True


class MetadataGuardError(ValueError):
    """Raised when a metadata document cannot be interpreted safely."""


def _read_json(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise MetadataGuardError(f"metadata file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise MetadataGuardError(f"invalid metadata JSON: {path}") from exc
    if not isinstance(value, dict):
        raise MetadataGuardError("metadata JSON must contain an object")
    return value


def _at(document: dict[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _same(expected: Any, observed: Any, path: str) -> bool:
    if path.endswith("variables"):
        return list(expected or []) == list(observed or [])
    if path.endswith("selected_value_m"):
        try:
            return abs(float(expected) - float(observed)) <= DEPTH_TOLERANCE_M
        except (TypeError, ValueError):
            return False
    return expected == observed


def compare_metadata(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> tuple[MetadataChange, ...]:
    """Return critical differences between the approved baseline and candidate."""

    if not isinstance(baseline, dict) or not isinstance(candidate, dict):
        raise MetadataGuardError("baseline and candidate must be JSON objects")

    expected_fields: tuple[tuple[str, Any], ...] = (
        ("product_id", PRODUCT_ID),
        ("datasets.daily.id", DAILY_DATASET_ID),
        ("datasets.monthly.id", MONTHLY_DATASET_ID),
        ("datasets.daily.variables", list(CURRENT_VARIABLES)),
        ("datasets.monthly.variables", list(CURRENT_VARIABLES)),
        ("datasets.daily.units", CURRENT_UNITS),
        ("datasets.monthly.units", CURRENT_UNITS),
        ("depth.selected_value_m", ANALYSIS_DEPTH_M),
        ("project_period.start", PROJECT_PERIOD_START),
        ("project_period.end_exclusive", PROJECT_PERIOD_END_EXCLUSIVE),
    )

    changes: list[MetadataChange] = []
    for path, expected in expected_fields:
        observed = _at(candidate, path)
        if observed is None or not _same(expected, observed, path):
            changes.append(MetadataChange(path, expected, observed))

    # The local baseline is also checked so malformed evidence cannot become
    # an authority merely because it was committed earlier.
    for path, expected in expected_fields:
        observed = _at(baseline, path)
        if observed is None or not _same(expected, observed, path):
            changes.append(MetadataChange(f"baseline.{path}", expected, observed))

    return tuple(changes)


def render_result(changes: tuple[MetadataChange, ...]) -> str:
    """Render a value-safe, human-readable guard result."""

    status = "PASS_WITH_NOTES" if not changes else "BLOCKED"
    lines = [f"status={status}", f"critical_change_count={len(changes)}"]
    if not changes:
        lines.append(
            "evidence=All approved product, dataset, variable, unit, depth, and period fields match"
        )
    else:
        lines.append("evidence=Metadata compatibility failed closed; pipeline must stop")
        for change in changes:
            lines.append(f"change={change.path}")
    lines.append(
        "limitations=Comparison uses sanitized canonical JSON; no live metadata or NetCDF was accessed"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        changes = compare_metadata(_read_json(args.baseline), _read_json(args.candidate))
    except MetadataGuardError as exc:
        print(f"status=BLOCKED\nerror={exc}\nlimitations=No live metadata access was performed")
        return 2
    print(render_result(changes))
    return 2 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
