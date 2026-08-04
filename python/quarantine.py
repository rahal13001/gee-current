"""Offline quarantine manager for invalid Stage 3 local files.

Quarantine is an explicit local filesystem operation.  This module never
contacts a service, authenticates, downloads data, or updates SQLite
inventory.  Callers must provide the root and the file to move; tests use only
temporary directories.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from python.inventory import JobRecord


DEFAULT_QUARANTINE_ROOT = Path("data/quarantine")
_TIMESTAMP_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")


class QuarantineError(ValueError):
    """Raised when a local quarantine operation is unsafe or invalid."""


class QuarantineCollisionError(QuarantineError):
    """Raised when a quarantine timestamp or destination already exists."""


@dataclass(frozen=True)
class QuarantineRecord:
    """Result of one successful local quarantine move."""

    job_id: str
    reason: str
    source_relative_path: str
    quarantine_relative_path: str
    reason_relative_path: str
    quarantined_utc: str


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _validate_timestamp(value: str) -> str:
    if not isinstance(value, str) or _TIMESTAMP_PATTERN.fullmatch(value) is None:
        raise QuarantineError("quarantined_utc must use YYYYMMDDTHHMMSSZ format")
    return value


def _resolve_under(root: Path, target: Path, *, label: str) -> tuple[Path, str]:
    root_path = root.resolve()
    resolved = target.resolve()
    try:
        relative = resolved.relative_to(root_path).as_posix()
    except ValueError as exc:
        raise QuarantineError(f"{label} escapes quarantine root") from exc
    return resolved, relative


def _write_reason_json(path: Path, payload: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            prefix=".reason.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except (OSError, TypeError, ValueError) as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise QuarantineError(f"reason metadata write failed: {path}") from exc


def quarantine_file(
    source_path: str | Path,
    *,
    root: str | Path,
    job_id: str,
    reason: str,
    expected: Any = None,
    actual: Any = None,
    quarantined_utc: str | None = None,
    quarantine_root: str | Path = DEFAULT_QUARANTINE_ROOT,
) -> QuarantineRecord:
    """Move one local invalid file into a timestamped, no-overwrite quarantine.

    The source must be a regular non-symlink file under ``root``.  The target
    timestamp directory must not already exist, which prevents an existing
    quarantined file or reason record from being overwritten.
    """

    if not isinstance(job_id, str) or not job_id:
        raise QuarantineError("job_id must be a non-empty string")
    if not isinstance(reason, str) or not reason:
        raise QuarantineError("reason must be a non-empty string")

    root_path = Path(root).resolve()
    source, source_relative_path = _resolve_under(
        root_path, Path(source_path), label="source path"
    )
    if source_relative_path == ".":
        raise QuarantineError("source path must identify a file")
    if source.is_symlink() or not source.is_file():
        raise QuarantineError(f"source is not a regular local file: {source}")

    quarantine_root_path = Path(quarantine_root)
    if quarantine_root_path.is_absolute():
        raise QuarantineError("quarantine_root must be relative to root")
    quarantine_root_resolved, quarantine_root_relative = _resolve_under(
        root_path, root_path / quarantine_root_path, label="quarantine root"
    )
    if source_relative_path == quarantine_root_relative or source_relative_path.startswith(
        f"{quarantine_root_relative}/"
    ):
        raise QuarantineError("source is already inside quarantine root")

    timestamp = _validate_timestamp(quarantined_utc or _utc_timestamp())
    quarantine_directory = quarantine_root_resolved / timestamp
    if quarantine_directory.exists():
        raise QuarantineCollisionError(f"quarantine timestamp already exists: {timestamp}")
    try:
        quarantine_directory.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise QuarantineCollisionError(f"quarantine timestamp already exists: {timestamp}") from exc
    except OSError as exc:
        raise QuarantineError(f"cannot create quarantine directory: {quarantine_directory}") from exc

    destination = quarantine_directory / source.name
    reason_path = quarantine_directory / "reason.json"
    quarantine_relative_path = destination.relative_to(root_path).as_posix()
    reason_relative_path = reason_path.relative_to(root_path).as_posix()
    payload: dict[str, Any] = {
        "job_id": job_id,
        "reason": reason,
        "source_relative_path": source_relative_path,
        "quarantine_relative_path": quarantine_relative_path,
        "quarantined_utc": timestamp,
    }
    if expected is not None:
        payload["expected"] = expected
    if actual is not None:
        payload["actual"] = actual

    try:
        _write_reason_json(reason_path, payload)
        if destination.exists():
            raise QuarantineCollisionError(f"quarantine destination already exists: {destination}")
        # os.rename is atomic on the same filesystem and, on the supported
        # Windows runtime, refuses to overwrite an existing destination.
        os.rename(source, destination)
    except QuarantineError:
        reason_path.unlink(missing_ok=True)
        quarantine_directory.rmdir()
        raise
    except OSError as exc:
        reason_path.unlink(missing_ok=True)
        quarantine_directory.rmdir()
        raise QuarantineError(f"atomic quarantine move failed: {source}") from exc

    return QuarantineRecord(
        job_id=job_id,
        reason=reason,
        source_relative_path=source_relative_path,
        quarantine_relative_path=quarantine_relative_path,
        reason_relative_path=reason_relative_path,
        quarantined_utc=timestamp,
    )


def quarantine_job(
    job: JobRecord,
    *,
    root: str | Path,
    reason: str,
    expected: Any = None,
    actual: Any = None,
    quarantined_utc: str | None = None,
    quarantine_root: str | Path = DEFAULT_QUARANTINE_ROOT,
) -> QuarantineRecord:
    """Quarantine the output path declared by one local inventory job."""

    source = Path(root) / job.output_directory / job.output_filename
    return quarantine_file(
        source,
        root=root,
        job_id=job.job_id,
        reason=reason,
        expected=expected,
        actual=actual,
        quarantined_utc=quarantined_utc,
        quarantine_root=quarantine_root,
    )


__all__ = [
    "DEFAULT_QUARANTINE_ROOT",
    "QuarantineCollisionError",
    "QuarantineError",
    "QuarantineRecord",
    "quarantine_file",
    "quarantine_job",
]
