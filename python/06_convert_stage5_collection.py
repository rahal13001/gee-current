"""Convert the complete validated Stage 5 collection locally and offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from python.conversion import config_hash, convert_collection, _atomic_write_json


def parse_args() -> argparse.Namespace:
    """Parse the collection conversion command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--config-file", type=Path, action="append", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--expected-jobs", type=int, default=165)
    parser.add_argument("--expected-timesteps", type=int, default=1125)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run the fail-closed collection conversion."""

    args = parse_args()
    report = convert_collection(
        root=args.root,
        manifest_path=args.manifest,
        output_root=args.output_root,
        config_hash_value=config_hash(args.config_file, root=args.root),
        expected_job_count=args.expected_jobs,
        expected_timestep_count=args.expected_timesteps,
        overwrite=args.overwrite,
        resume=args.resume,
    )
    _atomic_write_json(args.report, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
