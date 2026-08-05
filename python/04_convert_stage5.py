"""CLI for one offline Stage 5 conversion-pilot manifest job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from python.conversion import config_hash, convert_job, load_manifest_entry


def parse_args() -> argparse.Namespace:
    """Parse the local-only conversion command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--config-file", type=Path, action="append", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run one manifest-scoped conversion and write its JSON evidence."""

    args = parse_args()
    entry = load_manifest_entry(args.manifest, args.job_id)
    report = convert_job(
        root=args.root,
        entry=entry,
        output_dir=args.output_dir,
        config_hash_value=config_hash(args.config_file, root=args.root),
        prefix=args.prefix,
        overwrite=args.overwrite,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
