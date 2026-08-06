"""Create the offline T6-004 source and derived sample manifests."""

from __future__ import annotations

import argparse
from pathlib import Path

from gee_manifest import ManifestError, write_sample_manifests


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build T6-004 sample manifests locally; never upload or start an Earth Engine task."
    )
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root")
    parser.add_argument("--gcs-bucket", required=True, help="approved or explicitly sample GCS bucket name")
    parser.add_argument(
        "--created-utc",
        required=True,
        help="explicit manifest creation timestamp, for example 2026-08-06T00:00:00Z",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/manifests/stage_6_t6_004"),
        help="local output directory inside the repository",
    )
    args = parser.parse_args()
    try:
        index = write_sample_manifests(
            args.root,
            output_dir=args.output_dir,
            gcs_bucket=args.gcs_bucket,
            created_utc=args.created_utc,
        )
    except ManifestError as exc:
        parser.error(str(exc))
    print(f"stage={index['stage']}")
    print(f"status={index['status']}")
    print(f"sample_count={index['sample_count']}")
    print(f"output_dir={Path(args.output_dir).as_posix()}")
    print("limitations=No Earth Engine authentication, upload, export, or cloud task was executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
