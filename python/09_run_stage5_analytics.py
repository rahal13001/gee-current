"""Run offline Stage 5 analytics and precomputed products."""

from __future__ import annotations

import argparse
from pathlib import Path

from python.analytics import run_collection_analytics
from python.conversion import config_hash


def parse_args() -> argparse.Namespace:
    """Parse the local analytics command line."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conversion-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--config-file", type=Path, action="append", required=True)
    parser.add_argument("--analysis-period", type=Path, default=Path("config/analysis_period.json"))
    parser.add_argument("--study-area", type=Path, default=Path("config/study_area.json"))
    parser.add_argument("--statistics", type=Path, default=Path("config/statistics.json"))
    parser.add_argument("--depth-selection", type=Path, default=Path("config/depth_selection.json"))
    parser.add_argument("--local-config", type=Path, default=Path("config/local.example.json"))
    parser.add_argument("--ddof", type=int, default=0)
    parser.add_argument("--percentile-method", default="linear")
    return parser.parse_args()


def main() -> int:
    """Run the analytics collection pipeline."""

    args = parse_args()
    config_paths = list(args.config_file)
    for required_config in (args.analysis_period, args.study_area, args.statistics, args.depth_selection, args.local_config):
        if required_config not in config_paths:
            config_paths.append(required_config)
    run_collection_analytics(
        conversion_manifest_path=args.conversion_manifest,
        output_root=args.output_root,
        report_path=args.report,
        config_hash_value=config_hash(config_paths, root=Path.cwd()),
        ddof=args.ddof,
        percentile_method=args.percentile_method,
        analysis_period_path=args.analysis_period,
        study_area_path=args.study_area,
        statistics_path=args.statistics,
        depth_selection_path=args.depth_selection,
        local_config_path=args.local_config,
    )
    print(f"Analytics report written: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
