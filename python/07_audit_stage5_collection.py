"""Audit all local Stage 5 collection outputs and their inventory checksums."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from python.conversion import _atomic_write_json, audit_collection_outputs


def parse_args() -> argparse.Namespace:
    """Parse the collection audit command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conversion-report", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Run the structural, metadata, and checksum audit."""

    args = parse_args()
    conversion_report = json.loads(args.conversion_report.read_text(encoding="utf-8"))
    report = audit_collection_outputs(
        conversion_report=conversion_report,
        output_root=args.output_root,
    )
    _atomic_write_json(args.report, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
