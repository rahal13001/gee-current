"""Audit all Stage 5 analytics products from their provenance manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from python.analytics import audit_analytics_manifest
from python.conversion import _atomic_write_json


def parse_args() -> argparse.Namespace:
    """Parse the analytics audit command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Run the analytics product audit."""

    args = parse_args()
    report = audit_analytics_manifest(args.manifest)
    _atomic_write_json(args.report, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
