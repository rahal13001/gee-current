"""Offline dataset version/part pinning for Stage 3 batches.

The pin is derived only from the approved local metadata snapshot and is
checked against every locally supplied plan or inventory row.  A mismatch
raises an error before a caller can continue a batch.  This module never
authenticates, contacts Copernicus Marine or Earth Engine, downloads data, or
reads credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping


METADATA_SNAPSHOT = "outputs/evidence/stage_0/metadata_snapshot_2026-08-03.json"
MANIFEST_VERSION = 1


class DatasetPinError(ValueError):
    """Raised when a local dataset pin is missing or inconsistent."""


@dataclass(frozen=True)
class DatasetPin:
    """Immutable version/part pair approved for one local batch."""

    dataset_version: str
    dataset_part: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("dataset_version", self.dataset_version),
            ("dataset_part", self.dataset_part),
        ):
            if not isinstance(value, str) or not value.strip() or value != value.strip():
                raise DatasetPinError(f"{field_name} must be a non-empty trimmed string")

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> "DatasetPin":
        """Create a pin from the sanitized local metadata snapshot."""

        if not isinstance(snapshot, Mapping):
            raise DatasetPinError("metadata snapshot must be an object")
        version = snapshot.get("metadata_version")
        part = snapshot.get("dataset_version_part")
        if not isinstance(version, str) or not version.strip():
            raise DatasetPinError("metadata snapshot dataset version is missing")
        if not isinstance(part, str) or not part.strip():
            raise DatasetPinError("metadata snapshot dataset part is missing")
        return cls(dataset_version=version, dataset_part=part)


def load_dataset_pin(root: str | Path) -> DatasetPin:
    """Load a dataset pin from the approved local snapshot below ``root``."""

    path = Path(root) / METADATA_SNAPSHOT
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DatasetPinError(f"metadata snapshot not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DatasetPinError(f"invalid metadata snapshot: {path}") from exc
    return DatasetPin.from_snapshot(snapshot)


def _value(job: Mapping[str, Any] | Any, field: str) -> Any:
    if isinstance(job, Mapping):
        return job.get(field)
    return getattr(job, field, None)


def validate_job_pin(job: Mapping[str, Any] | Any, pin: DatasetPin) -> None:
    """Fail closed when one plan or inventory row differs from ``pin``."""

    observed_version = _value(job, "dataset_version")
    observed_part = _value(job, "dataset_part")
    if observed_version != pin.dataset_version:
        raise DatasetPinError(
            "dataset version changed during batch: "
            f"expected {pin.dataset_version!r}, observed {observed_version!r}"
        )
    if observed_part != pin.dataset_part:
        raise DatasetPinError(
            "dataset part changed during batch: "
            f"expected {pin.dataset_part!r}, observed {observed_part!r}"
        )


def validate_batch_pin(
    jobs: Iterable[Mapping[str, Any] | Any], pin: DatasetPin
) -> tuple[Mapping[str, Any] | Any, ...]:
    """Validate all jobs before a batch proceeds and return them unchanged."""

    batch = tuple(jobs)
    if not batch:
        raise DatasetPinError("cannot validate an empty batch")
    for job in batch:
        validate_job_pin(job, pin)
    return batch


def build_manifest(
    jobs: Iterable[Mapping[str, Any] | Any],
    pin: DatasetPin,
    *,
    created_utc: str,
) -> dict[str, Any]:
    """Build a deterministic local manifest for one pinned batch."""

    batch = validate_batch_pin(jobs, pin)
    if not isinstance(created_utc, str) or not created_utc.strip():
        raise DatasetPinError("manifest created_utc must be a non-empty string")
    job_ids = [_value(job, "job_id") for job in batch]
    if any(not isinstance(job_id, str) or not job_id for job_id in job_ids):
        raise DatasetPinError("every pinned job must have a non-empty job_id")
    if len(set(job_ids)) != len(job_ids):
        raise DatasetPinError("pinned batch contains duplicate job_id values")
    return {
        "manifest_version": MANIFEST_VERSION,
        "dataset_version": pin.dataset_version,
        "dataset_part": pin.dataset_part,
        "job_count": len(job_ids),
        "job_ids": sorted(job_ids),
        "created_utc": created_utc,
    }


def validate_manifest_pin(manifest: Mapping[str, Any], pin: DatasetPin) -> None:
    """Fail closed if a persisted batch manifest no longer matches ``pin``."""

    if not isinstance(manifest, Mapping):
        raise DatasetPinError("batch manifest must be an object")
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise DatasetPinError("unsupported batch manifest version")
    if manifest.get("dataset_version") != pin.dataset_version:
        raise DatasetPinError("batch manifest dataset version does not match pin")
    if manifest.get("dataset_part") != pin.dataset_part:
        raise DatasetPinError("batch manifest dataset part does not match pin")
    job_ids = manifest.get("job_ids")
    if not isinstance(job_ids, list) or not job_ids or any(
        not isinstance(job_id, str) or not job_id for job_id in job_ids
    ):
        raise DatasetPinError("batch manifest job_ids must be a non-empty string list")
    if manifest.get("job_count") != len(job_ids):
        raise DatasetPinError("batch manifest job_count does not match job_ids")
    if len(set(job_ids)) != len(job_ids) or job_ids != sorted(job_ids):
        raise DatasetPinError("batch manifest job_ids must be unique and sorted")
    created_utc = manifest.get("created_utc")
    if not isinstance(created_utc, str) or not created_utc.strip():
        raise DatasetPinError("batch manifest created_utc must be a non-empty string")


def write_manifest(
    path: str | Path,
    jobs: Iterable[Mapping[str, Any] | Any],
    pin: DatasetPin,
    *,
    created_utc: str,
) -> Path:
    """Atomically write a JSON manifest to an explicit local path."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(jobs, pin, created_utc=created_utc)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(manifest, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
        temporary_path.replace(target)
    except OSError as exc:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise DatasetPinError(f"could not write batch manifest: {target}") from exc
    return target


def read_manifest(path: str | Path) -> dict[str, Any]:
    """Read and structurally validate a local batch manifest."""

    target = Path(path)
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DatasetPinError(f"batch manifest not found: {target}") from exc
    except json.JSONDecodeError as exc:
        raise DatasetPinError(f"invalid batch manifest: {target}") from exc
    if not isinstance(value, dict):
        raise DatasetPinError("batch manifest must be an object")
    validate_manifest_pin(
        value,
        DatasetPin.from_snapshot(
            {
                "metadata_version": value.get("dataset_version"),
                "dataset_version_part": value.get("dataset_part"),
            }
        ),
    )
    return value
