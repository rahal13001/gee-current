"""CLI comparator for Stage 5 NetCDF-to-GeoTIFF pilot outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from python.conversion import compare_job_outputs
from python.conversion import load_manifest_entry


def parse_args() -> argparse.Namespace:
    """Parse the local-only comparison command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--geotiff-dir", type=Path, required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    return parser.parse_args()


def main() -> int:
    """Compare every pilot output against the decoded NetCDF source."""

    args = parse_args()
    entry = load_manifest_entry(args.manifest, args.job_id)
    report = compare_job_outputs(
        root=args.root,
        entry=entry,
        geotiff_dir=args.geotiff_dir,
        prefix=args.prefix,
        tolerance=args.tolerance,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
