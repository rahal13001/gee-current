"""Offline SQLite inventory for Stage 3 download-plan jobs.

This module only records locally supplied plan rows and state transitions. It
does not authenticate, contact Copernicus Marine or Earth Engine, download
data, inspect credentials, or enable the ``daily_full`` plan.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Iterable, Mapping, Any


INVENTORY_COLUMNS = (
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

STATUSES = (
    "planned",
    "preflight_passed",
    "downloading",
    "downloaded",
    "basic_check_passed",
    "checksum_recorded",
    "skipped_valid",
    "retry_wait",
    "failed_retryable",
    "failed_permanent",
    "quarantined",
    "ready_for_stage4",
)

ALLOWED_TRANSITIONS = {
    "planned": frozenset({"preflight_passed", "skipped_valid"}),
    "preflight_passed": frozenset({"downloading"}),
    "downloading": frozenset({"downloaded", "failed_retryable"}),
    "downloaded": frozenset({"basic_check_passed", "quarantined"}),
    "basic_check_passed": frozenset({"checksum_recorded"}),
    "checksum_recorded": frozenset({"ready_for_stage4"}),
    "skipped_valid": frozenset({"ready_for_stage4"}),
    "retry_wait": frozenset({"downloading"}),
    "failed_retryable": frozenset({"retry_wait", "failed_permanent"}),
    "failed_permanent": frozenset(),
    "quarantined": frozenset({"downloading"}),
    "ready_for_stage4": frozenset(),
}

_PLAN_NAMES = frozenset({"monthly_all", "daily_jfm"})


class InventoryError(ValueError):
    """Base error for invalid inventory operations."""


class InventoryValidationError(InventoryError):
    """Raised when a plan row does not satisfy the inventory schema."""


class InventoryTransitionError(InventoryError):
    """Raised when a job attempts an illegal status transition."""


@dataclass(frozen=True)
class JobRecord:
    """Typed view of one row in the download inventory."""

    job_id: str
    plan_name: str
    dataset_id: str
    year: int
    month: int
    start_datetime: str
    end_datetime: str
    expected_timesteps: int
    output_directory: str
    output_filename: str
    status: str
    attempt_count: int
    checksum: str
    dataset_version: str
    dataset_part: str
    created_utc: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "JobRecord":
        """Build a record from a SQLite row."""

        return cls(**{column: row[column] for column in INVENTORY_COLUMNS})


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS download_inventory (
    job_id TEXT PRIMARY KEY,
    plan_name TEXT NOT NULL CHECK (plan_name IN ('monthly_all', 'daily_jfm')),
    dataset_id TEXT NOT NULL CHECK (length(dataset_id) > 0),
    year INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 9999),
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    start_datetime TEXT NOT NULL CHECK (length(start_datetime) > 0),
    end_datetime TEXT NOT NULL CHECK (length(end_datetime) > 0),
    expected_timesteps INTEGER NOT NULL CHECK (expected_timesteps > 0),
    output_directory TEXT NOT NULL CHECK (length(output_directory) > 0),
    output_filename TEXT NOT NULL CHECK (length(output_filename) > 0),
    status TEXT NOT NULL DEFAULT 'planned' CHECK (
        status IN (
            'planned', 'preflight_passed', 'downloading', 'downloaded',
            'basic_check_passed', 'checksum_recorded', 'skipped_valid',
            'retry_wait', 'failed_retryable', 'failed_permanent',
            'quarantined', 'ready_for_stage4'
        )
    ),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    checksum TEXT NOT NULL DEFAULT '',
    dataset_version TEXT NOT NULL CHECK (length(dataset_version) > 0),
    dataset_part TEXT NOT NULL CHECK (length(dataset_part) > 0),
    created_utc TEXT NOT NULL CHECK (length(created_utc) > 0)
);

CREATE TRIGGER IF NOT EXISTS download_inventory_status_transition_guard
BEFORE UPDATE OF status ON download_inventory
FOR EACH ROW
WHEN OLD.status <> NEW.status
 AND NOT (
    (OLD.status = 'planned' AND NEW.status IN ('preflight_passed', 'skipped_valid'))
    OR (OLD.status = 'preflight_passed' AND NEW.status = 'downloading')
    OR (OLD.status = 'downloading' AND NEW.status IN ('downloaded', 'failed_retryable'))
    OR (OLD.status = 'downloaded' AND NEW.status IN ('basic_check_passed', 'quarantined'))
    OR (OLD.status = 'basic_check_passed' AND NEW.status = 'checksum_recorded')
    OR (OLD.status = 'checksum_recorded' AND NEW.status = 'ready_for_stage4')
    OR (OLD.status = 'skipped_valid' AND NEW.status = 'ready_for_stage4')
    OR (OLD.status = 'failed_retryable' AND NEW.status IN ('retry_wait', 'failed_permanent'))
    OR (OLD.status = 'retry_wait' AND NEW.status = 'downloading')
    OR (OLD.status = 'quarantined' AND NEW.status = 'downloading')
 )
BEGIN
    SELECT RAISE(ABORT, 'illegal inventory status transition');
END;
"""


def _validate_job(job: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize one locally generated plan row."""

    missing = [column for column in INVENTORY_COLUMNS if column not in job]
    if missing:
        raise InventoryValidationError(f"missing inventory columns: {', '.join(missing)}")

    normalized = {column: job[column] for column in INVENTORY_COLUMNS}
    if normalized["plan_name"] not in _PLAN_NAMES:
        raise InventoryValidationError("plan_name must be monthly_all or daily_jfm")
    if normalized["status"] != "planned":
        raise InventoryValidationError("new inventory jobs must start in planned")

    for column in (
        "job_id",
        "dataset_id",
        "start_datetime",
        "end_datetime",
        "output_directory",
        "output_filename",
        "dataset_version",
        "dataset_part",
        "created_utc",
    ):
        if not isinstance(normalized[column], str) or not normalized[column]:
            raise InventoryValidationError(f"{column} must be a non-empty string")

    try:
        normalized["year"] = int(normalized["year"])
        normalized["month"] = int(normalized["month"])
        normalized["expected_timesteps"] = int(normalized["expected_timesteps"])
        normalized["attempt_count"] = int(normalized["attempt_count"])
    except (TypeError, ValueError) as exc:
        raise InventoryValidationError("numeric inventory fields must be integers") from exc

    if not 1900 <= normalized["year"] <= 9999:
        raise InventoryValidationError("year must be between 1900 and 9999")
    if not 1 <= normalized["month"] <= 12:
        raise InventoryValidationError("month must be between 1 and 12")
    if normalized["expected_timesteps"] <= 0:
        raise InventoryValidationError("expected_timesteps must be positive")
    if normalized["attempt_count"] < 0:
        raise InventoryValidationError("attempt_count cannot be negative")
    if not isinstance(normalized["checksum"], str):
        raise InventoryValidationError("checksum must be a string")
    return normalized


class InventoryStore:
    """Manage the local SQLite transaction inventory without download side effects."""

    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)
        self._connection: sqlite3.Connection | None = None

    def __enter__(self) -> "InventoryStore":
        self.open()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the open connection for read-only inspection and testing."""

        if self._connection is None:
            raise InventoryError("inventory is not open")
        return self._connection

    def open(self) -> None:
        """Open the database and create the schema/triggers if needed."""

        if self._connection is not None:
            return
        database = Path(self.database_path)
        if self.database_path != ":memory:":
            database.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.executescript(_SCHEMA_SQL)
        self._connection.commit()

    def close(self) -> None:
        """Close the local database connection."""

        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def seed_jobs(self, jobs: Iterable[Mapping[str, Any]]) -> None:
        """Insert locally built plan rows, each initially in ``planned`` state."""

        rows = [_validate_job(job) for job in jobs]
        if not rows:
            return
        placeholders = ", ".join("?" for _ in INVENTORY_COLUMNS)
        statement = (
            f"INSERT INTO download_inventory ({', '.join(INVENTORY_COLUMNS)}) "
            f"VALUES ({placeholders})"
        )
        try:
            with self.connection:
                self.connection.executemany(
                    statement, [tuple(row[column] for column in INVENTORY_COLUMNS) for row in rows]
                )
        except sqlite3.IntegrityError as exc:
            raise InventoryValidationError(f"inventory insert rejected: {exc}") from exc

    def get_job(self, job_id: str) -> JobRecord | None:
        """Return one job by ID, or ``None`` when it is not present."""

        row = self.connection.execute(
            "SELECT * FROM download_inventory WHERE job_id = ?", (job_id,)
        ).fetchone()
        return JobRecord.from_row(row) if row is not None else None

    def list_jobs(self) -> tuple[JobRecord, ...]:
        """Return all jobs in deterministic job-ID order."""

        rows = self.connection.execute(
            "SELECT * FROM download_inventory ORDER BY job_id"
        ).fetchall()
        return tuple(JobRecord.from_row(row) for row in rows)

    def export_csv(self, path: str | Path) -> Path:
        """Export the current SQLite inventory as a deterministic CSV snapshot.

        The CSV is written beside the requested target and atomically replaced
        only after the complete header and row set has been flushed.
        """

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                prefix=f".{target.name}.",
                suffix=".tmp",
                dir=target.parent,
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                writer = csv.DictWriter(
                    handle,
                    fieldnames=INVENTORY_COLUMNS,
                    lineterminator="\n",
                )
                writer.writeheader()
                for job in self.list_jobs():
                    writer.writerow(
                        {column: getattr(job, column) for column in INVENTORY_COLUMNS}
                    )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, target)
        except OSError:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
        return target

    def transition(
        self,
        job_id: str,
        target_status: str,
        *,
        attempt_count: int | None = None,
        checksum: str | None = None,
    ) -> JobRecord:
        """Move one job through an allowed state transition.

        The transition is checked in Python for a useful error and again by a
        SQLite trigger so direct SQL updates cannot bypass the state machine.
        """

        if target_status not in STATUSES:
            raise InventoryTransitionError(f"unknown inventory status: {target_status}")
        current = self.get_job(job_id)
        if current is None:
            raise InventoryTransitionError(f"unknown inventory job: {job_id}")
        if (
            target_status != current.status
            and target_status not in ALLOWED_TRANSITIONS[current.status]
        ):
            raise InventoryTransitionError(
                f"illegal inventory status transition: {current.status} -> {target_status}"
            )

        next_attempt_count = current.attempt_count if attempt_count is None else attempt_count
        next_checksum = current.checksum if checksum is None else checksum
        if next_attempt_count < 0:
            raise InventoryValidationError("attempt_count cannot be negative")
        if not isinstance(next_checksum, str):
            raise InventoryValidationError("checksum must be a string")

        try:
            with self.connection:
                self.connection.execute(
                    """UPDATE download_inventory
                       SET status = ?, attempt_count = ?, checksum = ?
                       WHERE job_id = ?""",
                    (target_status, next_attempt_count, next_checksum, job_id),
                )
        except sqlite3.IntegrityError as exc:
            raise InventoryTransitionError(f"inventory transition rejected: {exc}") from exc
        updated = self.get_job(job_id)
        if updated is None:  # pragma: no cover - protected by the prior lookup
            raise InventoryError(f"inventory job disappeared during transition: {job_id}")
        return updated


__all__ = [
    "ALLOWED_TRANSITIONS",
    "INVENTORY_COLUMNS",
    "InventoryError",
    "InventoryStore",
    "InventoryTransitionError",
    "InventoryValidationError",
    "JobRecord",
    "STATUSES",
]
