"""Prepare the Stage 3 executor without performing a remote download.

This module is the offline preparation boundary for T3-014.  It builds the
approved local plan, optionally seeds the local SQLite inventory, and prints a
deterministic execution summary.  The actual Copernicus operation is
deliberately fail-closed in Foundation/M0: this module never logs in, reads
credentials, contacts a network service, or downloads data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import runpy
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from inventory import INVENTORY_COLUMNS, InventoryStore, JobRecord
except ModuleNotFoundError:
    from python.inventory import INVENTORY_COLUMNS, InventoryStore, JobRecord


ROOT = Path(__file__).resolve().parents[1]
PLAN_MODULE = runpy.run_path(str(Path(__file__).with_name("02_build_download_plan.py")))
build_plan = PLAN_MODULE["build_plan"]

DEFAULT_INVENTORY_PATH = Path("outputs/inventory/download_inventory.sqlite")
DEFAULT_INVENTORY_CSV = Path("outputs/inventory/download_inventory.csv")
MUTABLE_COLUMNS = frozenset({"status", "attempt_count", "checksum"})
EXECUTION_DISABLED = (
    "actual T3-014 download is disabled in Foundation/M0; "
    "network and authentication are not permitted"
)


class ExecutorPreparationError(ValueError):
    """Raised when local executor preparation cannot proceed safely."""


class ExecutionDisabledError(RuntimeError):
    """Raised when an actual remote execution is requested in offline mode."""


@dataclass(frozen=True)
class PlanSummary:
    """Deterministic local summary for one approved plan."""

    plan_name: str
    job_count: int
    expected_timesteps: int
    first_job: str
    last_job: str


def _relative_local_path(root: Path, value: str, *, label: str) -> Path:
    """Resolve a local output path and reject absolute/path-escaping targets."""

    candidate = Path(value)
    if candidate.is_absolute():
        raise ExecutorPreparationError(f"{label} must be relative: {value}")
    root_path = root.resolve()
    resolved = (root_path / candidate).resolve()
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise ExecutorPreparationError(f"{label} escapes repository root") from exc
    return resolved


def summarize_jobs(plan_name: str, jobs: Iterable[Mapping[str, Any]]) -> PlanSummary:
    """Validate basic plan shape and return a deterministic summary."""

    rows = tuple(jobs)
    if not rows:
        raise ExecutorPreparationError("plan contains no jobs")
    job_ids = tuple(str(row["job_id"]) for row in rows)
    if len(set(job_ids)) != len(job_ids):
        raise ExecutorPreparationError("plan contains duplicate job_id values")
    if any(row.get("plan_name") != plan_name for row in rows):
        raise ExecutorPreparationError("plan_name mismatch in local plan")
    return PlanSummary(
        plan_name=plan_name,
        job_count=len(rows),
        expected_timesteps=sum(int(row["expected_timesteps"]) for row in rows),
        first_job=min(job_ids),
        last_job=max(job_ids),
    )


def build_local_plan(
    root: str | Path,
    plan_name: str,
    *,
    created_utc: str | None = None,
) -> tuple[tuple[dict[str, Any], ...], PlanSummary]:
    """Build and validate a plan using only the approved local inputs."""

    root_path = Path(root).resolve()
    jobs = tuple(build_plan(root_path, plan_name, created_utc=created_utc))
    return jobs, summarize_jobs(plan_name, jobs)


def _immutable_values(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(row[column] for column in INVENTORY_COLUMNS if column not in MUTABLE_COLUMNS)


def _record_values(record: JobRecord) -> tuple[Any, ...]:
    return tuple(getattr(record, column) for column in INVENTORY_COLUMNS if column not in MUTABLE_COLUMNS)


def prepare_inventory(
    root: str | Path,
    jobs: Iterable[Mapping[str, Any]],
    *,
    inventory_path: str | Path = DEFAULT_INVENTORY_PATH,
    inventory_csv: str | Path = DEFAULT_INVENTORY_CSV,
) -> tuple[int, bool]:
    """Seed or validate a local inventory without changing existing states.

    A fresh inventory is seeded from the local plan.  An existing inventory is
    accepted only when its immutable plan fields and complete job set match;
    mutable state, attempt count, and checksum are never overwritten.
    """

    root_path = Path(root).resolve()
    database = _relative_local_path(root_path, str(inventory_path), label="inventory path")
    csv_path = _relative_local_path(root_path, str(inventory_csv), label="inventory CSV path")
    rows = tuple(jobs)
    if not rows:
        raise ExecutorPreparationError("cannot prepare inventory from an empty plan")
    expected = {str(row["job_id"]): row for row in rows}

    with InventoryStore(database) as store:
        existing = store.list_jobs()
        existing_by_id = {record.job_id: record for record in existing}
        if existing:
            if set(existing_by_id) != set(expected):
                raise ExecutorPreparationError(
                    "existing inventory job set does not match the local plan"
                )
            for job_id, row in expected.items():
                if _immutable_values(row) != _record_values(existing_by_id[job_id]):
                    raise ExecutorPreparationError(
                        f"existing inventory immutable fields mismatch: {job_id}"
                    )
            seeded = False
        else:
            store.seed_jobs(rows)
            seeded = True
        store.export_csv(csv_path)
        count = len(store.list_jobs())
    return count, seeded


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--plan",
        choices=("monthly_all", "daily_jfm", "daily_full"),
        required=True,
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--prepare-inventory",
        action="store_true",
        help="seed/validate local SQLite and CSV inventory; never contacts a service",
    )
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--inventory-csv", type=Path, default=DEFAULT_INVENTORY_CSV)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.prepare_inventory and not args.dry_run:
        print("error=--prepare-inventory requires --dry-run")
        return 2
    try:
        jobs, summary = build_local_plan(args.root, args.plan)
        print(f"stage=T3-014")
        print(f"plan={summary.plan_name}")
        print(f"job_count={summary.job_count}")
        print(f"expected_timesteps={summary.expected_timesteps}")
        print(f"first_job={summary.first_job}")
        print(f"last_job={summary.last_job}")
        if args.prepare_inventory:
            count, seeded = prepare_inventory(
                args.root,
                jobs,
                inventory_path=args.inventory,
                inventory_csv=args.inventory_csv,
            )
            print(f"inventory_rows={count}")
            print(f"inventory_action={'SEEDED' if seeded else 'VALIDATED_EXISTING'}")
        else:
            print("inventory_action=NOT_MODIFIED")
        print("authentication=NOT_PERFORMED")
        print("network=NOT_PERFORMED")
        print("download=NOT_PERFORMED")
        if args.dry_run:
            print("status=DRY_RUN_READY")
            return 0
        raise ExecutionDisabledError(EXECUTION_DISABLED)
    except ExecutionDisabledError as exc:
        print(f"error={exc}")
        return 3
    except (ExecutorPreparationError, OSError, ValueError) as exc:
        print(f"error={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

