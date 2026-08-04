"""Offline SHA-256 generation for Stage 3 local output files.

The generator reads only explicitly supplied local paths.  It does not
authenticate, access network services, download data, or mutate the SQLite
inventory.  Inventory integration can consume the returned records later
when the download executor is implemented.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hmac
import hashlib
import os
from pathlib import Path
import re
import tempfile
from typing import Iterable

from python.inventory import JobRecord


CHECKSUM_COLUMNS = (
    "job_id",
    "relative_path",
    "size_bytes",
    "sha256",
    "calculated_utc",
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_CHUNK_SIZE = 1024 * 1024


class ChecksumError(ValueError):
    """Raised when a checksum target or manifest record is invalid."""


@dataclass(frozen=True)
class ChecksumRecord:
    """One manifest row for a locally hashed inventory job."""

    job_id: str
    relative_path: str
    size_bytes: int
    sha256: str
    calculated_utc: str


def _validate_chunk_size(chunk_size: int) -> None:
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise ChecksumError("chunk_size must be a positive integer")


def sha256_file(path: str | Path, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Return the lowercase SHA-256 hex digest of one regular local file."""

    _validate_chunk_size(chunk_size)
    target = Path(path)
    if not target.exists():
        raise ChecksumError(f"checksum target does not exist: {target}")
    if not target.is_file():
        raise ChecksumError(f"checksum target is not a regular file: {target}")

    digest = hashlib.sha256()
    try:
        with target.open("rb") as handle:
            for block in iter(lambda: handle.read(chunk_size), b""):
                digest.update(block)
    except OSError as exc:
        raise ChecksumError(f"checksum read failed for local target: {target}") from exc
    return digest.hexdigest()


def verify_sha256(
    path: str | Path,
    expected_sha256: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bool:
    """Return whether a local file matches a validated expected digest."""

    if SHA256_PATTERN.fullmatch(expected_sha256) is None:
        raise ChecksumError("expected_sha256 must be 64 lowercase hexadecimal characters")
    actual_sha256 = sha256_file(path, chunk_size=chunk_size)
    return hmac.compare_digest(actual_sha256, expected_sha256)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _job_target(root: Path, job: JobRecord) -> tuple[Path, str]:
    output_directory = Path(job.output_directory)
    output_filename = Path(job.output_filename)
    if output_directory.is_absolute() or output_filename.is_absolute():
        raise ChecksumError(f"job output path must be relative: {job.job_id}")

    root_path = root.resolve()
    target = (root_path / output_directory / output_filename).resolve()
    try:
        relative_path = target.relative_to(root_path).as_posix()
    except ValueError as exc:
        raise ChecksumError(f"job output path escapes checksum root: {job.job_id}") from exc
    return target, relative_path


def generate_job_checksums(
    jobs: Iterable[JobRecord],
    *,
    root: str | Path,
    calculated_utc: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[ChecksumRecord, ...]:
    """Hash inventory job outputs under ``root`` in deterministic job order."""

    _validate_chunk_size(chunk_size)
    root_path = Path(root)
    timestamp = _utc_now() if calculated_utc is None else calculated_utc
    if not isinstance(timestamp, str) or not timestamp:
        raise ChecksumError("calculated_utc must be a non-empty string")

    records: list[ChecksumRecord] = []
    seen_job_ids: set[str] = set()
    for job in sorted(jobs, key=lambda item: item.job_id):
        if job.job_id in seen_job_ids:
            raise ChecksumError(f"duplicate inventory job_id: {job.job_id}")
        seen_job_ids.add(job.job_id)
        target, relative_path = _job_target(root_path, job)
        try:
            size_before = target.stat().st_size
        except OSError as exc:
            raise ChecksumError(f"checksum target cannot be inspected: {target}") from exc
        digest = sha256_file(target, chunk_size=chunk_size)
        try:
            size_after = target.stat().st_size
        except OSError as exc:
            raise ChecksumError(f"checksum target changed or disappeared: {target}") from exc
        if size_before != size_after:
            raise ChecksumError(f"checksum target changed during hashing: {target}")
        records.append(
            ChecksumRecord(
                job_id=job.job_id,
                relative_path=relative_path,
                size_bytes=size_after,
                sha256=digest,
                calculated_utc=timestamp,
            )
        )
    return tuple(records)


def _validate_record(record: ChecksumRecord) -> None:
    if not record.job_id or not record.relative_path:
        raise ChecksumError("checksum record identifiers must be non-empty")
    if isinstance(record.size_bytes, bool) or not isinstance(record.size_bytes, int) or record.size_bytes < 0:
        raise ChecksumError("checksum record size_bytes must be a non-negative integer")
    if SHA256_PATTERN.fullmatch(record.sha256) is None:
        raise ChecksumError("checksum record sha256 must be 64 lowercase hexadecimal characters")
    if not record.calculated_utc:
        raise ChecksumError("checksum record calculated_utc must be non-empty")


def write_checksum_csv(records: Iterable[ChecksumRecord], path: str | Path) -> Path:
    """Write a validated, ordered checksum manifest using atomic replacement."""

    ordered = tuple(sorted(records, key=lambda record: record.job_id))
    seen_job_ids: set[str] = set()
    for record in ordered:
        _validate_record(record)
        if record.job_id in seen_job_ids:
            raise ChecksumError(f"duplicate checksum manifest job_id: {record.job_id}")
        seen_job_ids.add(record.job_id)

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
            writer = csv.DictWriter(handle, fieldnames=CHECKSUM_COLUMNS, lineterminator="\n")
            writer.writeheader()
            for record in ordered:
                writer.writerow({column: getattr(record, column) for column in CHECKSUM_COLUMNS})
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, target)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise ChecksumError(f"checksum manifest write failed: {target}") from exc
    return target


__all__ = [
    "CHECKSUM_COLUMNS",
    "ChecksumError",
    "ChecksumRecord",
    "DEFAULT_CHUNK_SIZE",
    "generate_job_checksums",
    "sha256_file",
    "verify_sha256",
    "write_checksum_csv",
]
