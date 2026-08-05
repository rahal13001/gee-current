"""Reconcile the local Stage 3 filesystem against the SQLite inventory.

This command is strictly local and read-only. It builds the approved local
plans, opens the existing SQLite database in read-only mode, checks inventory
identity/status, verifies every active output path and SHA-256 checksum, and
reports extra/missing files. It never changes inventory, moves quarantine
files, authenticates, contacts a service, or downloads data.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import runpy
import sqlite3
import sys
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.checksum import ChecksumError, sha256_file
from python.inventory import INVENTORY_COLUMNS, JobRecord


DEFAULT_INVENTORY_PATH = Path("outputs/inventory/download_inventory.sqlite")
PLAN_MODULE = runpy.run_path(str(Path(__file__).with_name("02_build_download_plan.py")))
build_plan = PLAN_MODULE["build_plan"]
PlanError = PLAN_MODULE["PlanError"]

PLAN_NAMES = ("monthly_all", "daily_jfm")
PLAN_OUTPUT_ROOTS = {
    "monthly_all": Path("data/raw/monthly"),
    "daily_jfm": Path("data/raw/daily_jfm"),
}
MUTABLE_COLUMNS = frozenset({"status", "attempt_count", "checksum", "created_utc"})
QUARANTINE_NOTE_CODE = "QUARANTINE_ARTIFACTS"


class ReconciliationError(ValueError):
    """Raised when local reconciliation cannot be performed safely."""


@dataclass(frozen=True)
class ReconciliationIssue:
    """One deterministic reconciliation finding."""

    code: str
    severity: str
    detail: str


@dataclass(frozen=True)
class ReconciliationReport:
    """Read-only reconciliation result."""

    plans: tuple[str, ...]
    expected_jobs: int
    inventory_jobs: int
    ready_jobs: int
    expected_timesteps: int
    active_files: int
    checksum_matches: int
    quarantine_files: int
    partial_files: int
    issues: tuple[ReconciliationIssue, ...]

    @property
    def blocking_issues(self) -> tuple[ReconciliationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == "ERROR")

    @property
    def status(self) -> str:
        if self.blocking_issues:
            return "FAIL"
        return "PASS_WITH_NOTES" if self.issues else "PASS"


def _resolve_under_root(root: Path, value: str | Path, *, label: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise ReconciliationError(f"{label} must be relative to repository root")
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ReconciliationError(f"{label} escapes repository root") from exc
    return resolved


def _job_target(root: Path, job: JobRecord) -> Path:
    directory = _resolve_under_root(root, job.output_directory, label="output directory")
    filename = Path(job.output_filename)
    if filename.is_absolute() or filename.name != job.output_filename:
        raise ReconciliationError(f"unsafe output filename in inventory: {job.job_id}")
    target = (directory / filename).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ReconciliationError(f"output path escapes repository root: {job.job_id}") from exc
    return target


def _immutable_values(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(row[column] for column in INVENTORY_COLUMNS if column not in MUTABLE_COLUMNS)


def _record_values(record: JobRecord) -> tuple[Any, ...]:
    return tuple(getattr(record, column) for column in INVENTORY_COLUMNS if column not in MUTABLE_COLUMNS)


def _read_only_jobs(database: Path) -> tuple[JobRecord, ...]:
    if not database.is_file():
        raise ReconciliationError(f"inventory database does not exist: {database}")
    uri = f"file:{database.as_posix()}?mode=ro"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise ReconciliationError(f"cannot open inventory read-only: {database}") from exc
    connection.row_factory = sqlite3.Row
    try:
        columns = tuple(row["name"] for row in connection.execute("PRAGMA table_info(download_inventory)"))
        if columns != INVENTORY_COLUMNS:
            raise ReconciliationError("inventory schema columns do not match the approved schema")
        rows = connection.execute(
            "SELECT * FROM download_inventory ORDER BY job_id"
        ).fetchall()
        return tuple(JobRecord.from_row(row) for row in rows)
    except sqlite3.Error as exc:
        raise ReconciliationError("cannot read inventory database") from exc
    finally:
        connection.close()


def _expected_plan(root: Path, plan_name: str) -> tuple[dict[str, Any], ...]:
    try:
        return tuple(build_plan(root, plan_name, created_utc="2026-08-05T00:00:00Z"))
    except (PlanError, OSError, ValueError) as exc:
        raise ReconciliationError(f"cannot build local {plan_name} plan: {exc}") from exc


def _append_issue(
    issues: list[ReconciliationIssue],
    code: str,
    detail: str,
    *,
    severity: str = "ERROR",
) -> None:
    issues.append(ReconciliationIssue(code, severity, detail))


def reconcile(
    root: str | Path,
    *,
    plan_name: str | None = None,
    inventory_path: str | Path = DEFAULT_INVENTORY_PATH,
) -> ReconciliationReport:
    """Compare active local files and checksums with the read-only inventory."""

    root_path = Path(root).resolve()
    plans = PLAN_NAMES if plan_name is None else (plan_name,)
    if any(name not in PLAN_NAMES for name in plans):
        raise ReconciliationError(f"unsupported reconciliation plan: {plan_name}")

    expected_rows = tuple(row for name in plans for row in _expected_plan(root_path, name))
    expected_by_id = {str(row["job_id"]): row for row in expected_rows}
    if len(expected_by_id) != len(expected_rows):
        raise ReconciliationError("local plans contain duplicate job IDs")

    database = _resolve_under_root(root_path, inventory_path, label="inventory path")
    inventory_rows = _read_only_jobs(database)
    scoped_inventory = tuple(record for record in inventory_rows if record.plan_name in plans)
    inventory_by_id = {record.job_id: record for record in scoped_inventory}
    issues: list[ReconciliationIssue] = []

    missing_inventory = sorted(set(expected_by_id) - set(inventory_by_id))
    if missing_inventory:
        _append_issue(
            issues,
            "INVENTORY_MISSING_JOB",
            f"{len(missing_inventory)} expected job(s) missing from inventory: {','.join(missing_inventory)}",
        )
    unexpected_inventory = sorted(set(inventory_by_id) - set(expected_by_id))
    if unexpected_inventory:
        _append_issue(
            issues,
            "INVENTORY_UNEXPECTED_JOB",
            f"{len(unexpected_inventory)} inventory job(s) absent from local plan: {','.join(unexpected_inventory)}",
        )
    for job_id in sorted(set(expected_by_id) & set(inventory_by_id)):
        if _immutable_values(expected_by_id[job_id]) != _record_values(inventory_by_id[job_id]):
            _append_issue(issues, "INVENTORY_PLAN_MISMATCH", f"immutable plan fields mismatch: {job_id}")

    expected_paths: dict[Path, JobRecord] = {}
    ready_jobs = 0
    expected_timesteps = 0
    checksum_matches = 0
    active_files = 0
    for job_id in sorted(expected_by_id):
        row = expected_by_id[job_id]
        expected_timesteps += int(row["expected_timesteps"])
        record = inventory_by_id.get(job_id)
        if record is None:
            continue
        target = _job_target(root_path, record)
        expected_paths[target] = record
        if record.status == "ready_for_stage4":
            ready_jobs += 1
        else:
            _append_issue(
                issues,
                "INVENTORY_STATUS_NOT_READY",
                f"{job_id} has status {record.status}, expected ready_for_stage4",
            )
        if not record.checksum:
            _append_issue(issues, "INVENTORY_CHECKSUM_MISSING", f"checksum is empty: {job_id}")
        if target.is_symlink() or not target.is_file():
            _append_issue(issues, "ACTIVE_FILE_MISSING", f"active output is missing or not regular: {target}")
            continue
        active_files += 1
        try:
            actual = sha256_file(target)
        except ChecksumError as exc:
            _append_issue(issues, "ACTIVE_FILE_UNREADABLE", f"{job_id}: {exc}")
            continue
        if actual != record.checksum:
            _append_issue(issues, "CHECKSUM_MISMATCH", f"{job_id}: inventory checksum differs from active file")
        else:
            checksum_matches += 1

    raw_files: set[Path] = set()
    for name in plans:
        raw_root = _resolve_under_root(root_path, PLAN_OUTPUT_ROOTS[name], label="raw output root")
        if raw_root.exists():
            raw_files.update(path.resolve() for path in raw_root.rglob("*.nc") if path.is_file())
    extra_files = sorted(raw_files - set(expected_paths))
    if extra_files:
        _append_issue(
            issues,
            "ACTIVE_FILE_EXTRA",
            f"{len(extra_files)} unexpected active NetCDF file(s): {','.join(str(path.relative_to(root_path)) for path in extra_files)}",
        )

    partial_files = 0
    partial_root = root_path / "data" / "partial"
    if partial_root.exists():
        partial_files = sum(1 for path in partial_root.rglob("*") if path.is_file())
    if partial_files:
        _append_issue(issues, "PARTIAL_FILES_PRESENT", f"{partial_files} file(s) remain under data/partial")

    quarantine_root = root_path / "data" / "quarantine"
    quarantine_files = 0
    if quarantine_root.exists():
        quarantine_files = sum(1 for path in quarantine_root.rglob("*.nc") if path.is_file())
    if quarantine_files:
        _append_issue(
            issues,
            QUARANTINE_NOTE_CODE,
            f"{quarantine_files} quarantined NetCDF artifact(s) retained as audit evidence",
            severity="NOTE",
        )

    return ReconciliationReport(
        plans=tuple(plans),
        expected_jobs=len(expected_rows),
        inventory_jobs=len(scoped_inventory),
        ready_jobs=ready_jobs,
        expected_timesteps=expected_timesteps,
        active_files=active_files,
        checksum_matches=checksum_matches,
        quarantine_files=quarantine_files,
        partial_files=partial_files,
        issues=tuple(issues),
    )


def render_report(report: ReconciliationReport) -> str:
    """Render a stable text report suitable for evidence capture."""

    lines = [
        "stage=T3-016",
        f"plans={','.join(report.plans)}",
        f"expected_jobs={report.expected_jobs}",
        f"inventory_jobs={report.inventory_jobs}",
        f"ready_jobs={report.ready_jobs}",
        f"expected_timesteps={report.expected_timesteps}",
        f"active_files={report.active_files}",
        f"checksum_matches={report.checksum_matches}",
        f"quarantine_files={report.quarantine_files}",
        f"partial_files={report.partial_files}",
        f"issue_count={len(report.issues)}",
    ]
    for issue in report.issues:
        lines.append(f"issue={issue.severity}|{issue.code}|{issue.detail}")
    lines.append(f"status={report.status}")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--plan", choices=("all", *PLAN_NAMES), default="all")
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = reconcile(
            args.root,
            plan_name=None if args.plan == "all" else args.plan,
            inventory_path=args.inventory,
        )
        print(render_report(report))
        return 0 if report.status != "FAIL" else 4
    except (ReconciliationError, OSError, sqlite3.Error) as exc:
        print(f"stage=T3-016")
        print(f"error={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

