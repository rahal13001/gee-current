"""Compare every local Stage 5 collection GeoTIFF against decoded NetCDF."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from python.conversion import _atomic_write_json, compare_collection_outputs


def parse_args() -> argparse.Namespace:
    """Parse the collection comparator command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    return parser.parse_args()


def main() -> int:
    """Run numeric comparison for all manifest jobs."""

    args = parse_args()
    report = compare_collection_outputs(
        root=args.root,
        manifest_path=args.manifest,
        output_root=args.output_root,
        tolerance=args.tolerance,
    )
    _atomic_write_json(args.report, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
