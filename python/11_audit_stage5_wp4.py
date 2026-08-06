"""Audit Stage 5 WP5-4 climatology, anomaly, and trend products."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from python.analytics import audit_wp4_products
from python.conversion import _atomic_write_json


def parse_args() -> argparse.Namespace:
    """Parse the WP5-4 audit command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analytics-manifest", type=Path, required=True)
    parser.add_argument("--conversion-manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """Run the WP5-4 acceptance audit."""

    args = parse_args()
    report = audit_wp4_products(args.analytics_manifest, args.conversion_manifest)
    _atomic_write_json(args.report, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
