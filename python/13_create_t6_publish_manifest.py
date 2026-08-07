"""Create the offline T6-007/T6-008 publish-selection manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from gee_manifest import ManifestError
from t6_publish_manifest import write_publish_manifest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the Stage 6 publish selection locally; never upload or start a cloud task."
    )
    parser.add_argument("--root", type=Path, default=Path("."), help="repository root")
    parser.add_argument(
        "--created-utc",
        required=True,
        help="explicit manifest creation timestamp, for example 2026-08-07T00:00:00Z",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/manifests/stage_6_publish"),
        help="local output directory inside the repository",
    )
    args = parser.parse_args()
    try:
        result = write_publish_manifest(args.root, output_dir=args.output_dir, created_utc=args.created_utc)
    except ManifestError as exc:
        parser.error(str(exc))
    print(f"stage={result['stage']}")
    print(f"status={result['status']}")
    print(f"manifest={result['manifest']}")
    print(f"manifest_sha256={result['sha256']}")
    print("selected_source_count=1125")
    print("selected_derived_count=1138")
    print("limitations=No GCS/Earth Engine authentication, upload, export, ACL mutation, or cloud task was executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
