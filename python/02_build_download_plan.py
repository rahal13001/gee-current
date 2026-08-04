"""Build deterministic Stage 3 download plans without network access.

This command only reads the approved local configuration and metadata snapshot.
It never logs in, reads credentials, calls Copernicus Marine, downloads data,
or enables the ``daily_full`` plan.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Iterable

try:
    from dataset_pin import DatasetPin, validate_batch_pin
except ModuleNotFoundError:
    from python.dataset_pin import DatasetPin, validate_batch_pin


PRODUCT_ID = "GLOBAL_MULTIYEAR_PHY_001_030"
DAILY_DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1D-m"
MONTHLY_DATASET_ID = "cmems_mod_glo_phy_my_0.083deg_P1M-m"
VARIABLES = ("uo", "vo")
DEPTH_M = 0.494025
DEPTH_TOLERANCE_M = 0.000001
METADATA_VERSION = "202311"
DATASET_PART = "default"
PLAN_COLUMNS = (
    "job_id",
    "plan_name",
    "dataset_id",
    "year",
    "month",
    "start_datetime",
    "end_datetime",
    "expected_timesteps",
    "output_directory",
    "output_filename",
    "status",
    "attempt_count",
    "checksum",
    "dataset_version",
    "dataset_part",
    "created_utc",
)


class PlanError(ValueError):
    """Raised when the approved local configuration cannot build a plan."""


class DailyFullDisabledError(PlanError):
    """Raised whenever the disabled full-daily plan is requested."""


DISABLED_PLAN_NAMES = frozenset({"daily_full"})


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PlanError(f"missing configuration: {relative}") from exc
    except json.JSONDecodeError as exc:
        raise PlanError(f"invalid JSON: {relative}") from exc
    if not isinstance(value, dict):
        raise PlanError(f"configuration must be an object: {relative}")
    return value


def _month_end(year: int, month: int) -> date:
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def _format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def _metadata(root: Path) -> dict[str, Any]:
    snapshot = _read_json(root, "outputs/evidence/stage_0/metadata_snapshot_2026-08-03.json")
    if snapshot.get("product_id") != PRODUCT_ID:
        raise PlanError("metadata snapshot product_id does not match approved baseline")
    if snapshot.get("metadata_version") != METADATA_VERSION:
        raise PlanError("metadata snapshot version does not match approved baseline")
    if snapshot.get("dataset_version_part") != DATASET_PART:
        raise PlanError("metadata snapshot part does not match approved baseline")
    DatasetPin.from_snapshot(snapshot)
    if snapshot.get("datasets", {}).get("daily", {}).get("id") != DAILY_DATASET_ID:
        raise PlanError("metadata snapshot daily dataset does not match approved baseline")
    if snapshot.get("datasets", {}).get("monthly", {}).get("id") != MONTHLY_DATASET_ID:
        raise PlanError("metadata snapshot monthly dataset does not match approved baseline")
    if tuple(snapshot.get("datasets", {}).get("daily", {}).get("variables", [])) != VARIABLES:
        raise PlanError("metadata snapshot variables do not match approved baseline")
    selected_depth = float(snapshot.get("depth", {}).get("selected_value_m", -1))
    if abs(selected_depth - DEPTH_M) > DEPTH_TOLERANCE_M:
        raise PlanError("metadata snapshot depth does not match approved baseline")
    return snapshot


def _period(root: Path) -> tuple[list[int], int, int]:
    period = _read_json(root, "config/analysis_period.json")
    years = period.get("years")
    if years != list(range(2015, 2026)):
        raise PlanError("analysis period must contain years 2015 through 2025")
    if period.get("monthly_count_expected") != 132:
        raise PlanError("monthly expected count must remain 132")
    if period.get("daily_jfm_count_expected") != 993:
        raise PlanError("daily JFM expected count must remain 993")
    if period.get("full_period", {}).get("end_exclusive") != "2026-01-01":
        raise PlanError("analysis period end must remain exclusive 2026-01-01")
    return years, int(period["monthly_count_expected"]), int(period["daily_jfm_count_expected"])


def _job(
    *,
    plan_name: str,
    year: int,
    month: int,
    dataset_id: str,
    expected_timesteps: int,
    output_directory: str,
    output_filename: str,
    created_utc: str,
    dataset_version: str,
    dataset_part: str,
) -> dict[str, Any]:
    start_day = date(year, month, 1)
    end_day = _month_end(year, month)
    return {
        "job_id": f"{plan_name.replace('_all', '')}_{year}_{month:02d}",
        "plan_name": plan_name,
        "dataset_id": dataset_id,
        "year": year,
        "month": month,
        "start_datetime": _format_datetime(datetime.combine(start_day, time.min)),
        "end_datetime": _format_datetime(datetime.combine(end_day, time.min) - timedelta(seconds=1)),
        "expected_timesteps": expected_timesteps,
        "output_directory": output_directory,
        "output_filename": output_filename,
        "status": "planned",
        "attempt_count": 0,
        "checksum": "",
        "dataset_version": dataset_version,
        "dataset_part": dataset_part,
        "created_utc": created_utc,
    }


def build_plan(root: Path, plan_name: str, *, created_utc: str | None = None) -> list[dict[str, Any]]:
    """Return the requested plan after validating local approved baselines."""

    if plan_name in DISABLED_PLAN_NAMES:
        raise DailyFullDisabledError(
            "daily_full is disabled and cannot be planned without approval/change control"
        )
    if plan_name not in {"monthly_all", "daily_jfm"}:
        raise PlanError(f"unsupported plan: {plan_name}")

    metadata = _metadata(root)
    pin = DatasetPin.from_snapshot(metadata)
    years, _, _ = _period(root)
    stamp = created_utc or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    jobs: list[dict[str, Any]] = []

    for year in years:
        months: Iterable[int] = range(1, 13) if plan_name == "monthly_all" else range(1, 4)
        dataset_id = MONTHLY_DATASET_ID if plan_name == "monthly_all" else DAILY_DATASET_ID
        output_kind = "monthly" if plan_name == "monthly_all" else "daily_jfm"
        for month in months:
            days = (_month_end(year, month) - date(year, month, 1)).days
            filename_prefix = "glorys12v1_monthly" if plan_name == "monthly_all" else "glorys12v1_daily"
            jobs.append(
                _job(
                    plan_name=plan_name,
                    year=year,
                    month=month,
                    dataset_id=dataset_id,
                    expected_timesteps=1 if plan_name == "monthly_all" else days,
                    output_directory=f"data/raw/{output_kind}/{year}",
                    output_filename=f"{filename_prefix}_{year}{month:02d}_d0p494025m.nc",
                    created_utc=stamp,
                    dataset_version=pin.dataset_version,
                    dataset_part=pin.dataset_part,
                )
            )
    return list(validate_batch_pin(jobs, pin))


def write_csv(jobs: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PLAN_COLUMNS)
        writer.writeheader()
        writer.writerows(jobs)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--plan", choices=("monthly_all", "daily_jfm", "daily_full"), required=True)
    parser.add_argument("--output", type=Path, help="Write CSV plan; omit for read-only summary")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing a plan")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        jobs = build_plan(args.root.resolve(), args.plan)
        if args.output and not args.dry_run:
            write_csv(jobs, args.output.resolve())
        total_timesteps = sum(int(job["expected_timesteps"]) for job in jobs)
        first, last = jobs[0], jobs[-1]
        print(f"plan={args.plan}")
        print(f"job_count={len(jobs)}")
        print(f"expected_timesteps={total_timesteps}")
        print(f"first_job={first['job_id']}")
        print(f"last_job={last['job_id']}")
        print(f"status={ 'DRY_RUN' if args.dry_run or not args.output else 'WRITTEN' }")
        if args.output and not args.dry_run:
            print(f"output={args.output.resolve()}")
        return 0
    except (PlanError, OSError) as exc:
        print(f"error={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
