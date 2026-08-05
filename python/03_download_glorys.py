"""Prepare and execute the Stage 3 Copernicus Marine download plan.

The default behavior is read-only preparation.  A remote operation requires
the explicit ``--execute`` flag.  The executor uses the local Copernicus
Marine configuration managed by the user; it never reads or prints
credentials.  ``daily_full`` remains rejected by the plan builder.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
import runpy
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.checksum import sha256_file
from python.inventory import INVENTORY_COLUMNS, InventoryStore, JobRecord
from python.log_sanitizer import render_event, sanitize_exception
from python.quarantine import quarantine_file
from python.retry_backoff import BackoffPolicy, DEFAULT_BACKOFF_POLICY
from python.retry_classifier import RetryDecision, classify_error


PLAN_MODULE = runpy.run_path(str(Path(__file__).with_name("02_build_download_plan.py")))
build_plan = PLAN_MODULE["build_plan"]
PlanError = PLAN_MODULE["PlanError"]

DEFAULT_INVENTORY_PATH = Path("outputs/inventory/download_inventory.sqlite")
DEFAULT_INVENTORY_CSV = Path("outputs/inventory/download_inventory.csv")
DEFAULT_LOG_DIRECTORY = Path("outputs/logs/jobs")
DEFAULT_PARTIAL_DIRECTORY = Path("data/partial")
VARIABLES = ("uo", "vo")
DEPTH_TOLERANCE_M = 0.000001
MUTABLE_COLUMNS = frozenset({"status", "attempt_count", "checksum"})
NON_IDENTITY_COLUMNS = MUTABLE_COLUMNS | frozenset({"created_utc"})


class ExecutorPreparationError(ValueError):
    """Raised when local executor preparation cannot proceed safely."""


class ExecutionDisabledError(RuntimeError):
    """Raised when an actual remote execution is not explicitly enabled."""


class DownloadExecutionError(RuntimeError):
    """Raised for a download or local output-integrity failure."""


class BatchExecutionError(RuntimeError):
    """Raised when a batch stops on an unrecoverable job failure."""


@dataclass(frozen=True)
class PlanSummary:
    """Deterministic local summary for one approved plan."""

    plan_name: str
    job_count: int
    expected_timesteps: int
    first_job: str
    last_job: str


@dataclass(frozen=True)
class AOIBounds:
    """Validated active bounding-box AOI."""

    west: float
    east: float
    south: float
    north: float


@dataclass(frozen=True)
class BasicCheck:
    """Minimal local output check required before checksum recording."""

    size_bytes: int
    timestep_count: int
    depth_m: float
    variables: tuple[str, ...]


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ExecutorPreparationError(f"missing local configuration: {relative}") from exc
    except json.JSONDecodeError as exc:
        raise ExecutorPreparationError(f"invalid local JSON: {relative}") from exc
    if not isinstance(value, dict):
        raise ExecutorPreparationError(f"local configuration must be an object: {relative}")
    return value


def load_runtime_config(root: str | Path) -> tuple[AOIBounds, float]:
    """Load and validate only the local AOI and depth configuration."""

    root_path = Path(root).resolve()
    study = _read_json(root_path, "config/study_area.json")
    if study.get("geometry_type") != "bbox":
        raise ExecutorPreparationError("active AOI must be a bbox for T3-014")
    try:
        aoi = AOIBounds(
            west=float(study["west"]),
            east=float(study["east"]),
            south=float(study["south"]),
            north=float(study["north"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ExecutorPreparationError("active AOI bbox is incomplete or non-numeric") from exc
    if not aoi.west < aoi.east or not aoi.south < aoi.north:
        raise ExecutorPreparationError("active AOI bbox ordering is invalid")
    if not -180 <= aoi.west <= 180 or not -180 <= aoi.east <= 180:
        raise ExecutorPreparationError("active AOI longitude is outside -180..180")
    if not -90 <= aoi.south <= 90 or not -90 <= aoi.north <= 90:
        raise ExecutorPreparationError("active AOI latitude is outside -90..90")

    depth_config = _read_json(root_path, "config/depth_selection.json")
    try:
        depth_m = float(depth_config["analysis_depth_m"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ExecutorPreparationError("analysis depth is missing or non-numeric") from exc
    if depth_m < 0:
        raise ExecutorPreparationError("analysis depth cannot be negative")
    return aoi, depth_m


def _relative_local_path(root: Path, value: str | Path, *, label: str) -> Path:
    """Resolve a relative local output path and reject path escapes."""

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
    """Build and validate a plan using only approved local inputs."""

    root_path = Path(root).resolve()
    jobs = tuple(build_plan(root_path, plan_name, created_utc=created_utc))
    return jobs, summarize_jobs(plan_name, jobs)


def _immutable_values(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(
        row[column]
        for column in INVENTORY_COLUMNS
        if column not in NON_IDENTITY_COLUMNS
    )


def _record_values(record: JobRecord) -> tuple[Any, ...]:
    return tuple(
        getattr(record, column)
        for column in INVENTORY_COLUMNS
        if column not in NON_IDENTITY_COLUMNS
    )


def prepare_inventory(
    root: str | Path,
    jobs: Iterable[Mapping[str, Any]],
    *,
    inventory_path: str | Path = DEFAULT_INVENTORY_PATH,
    inventory_csv: str | Path = DEFAULT_INVENTORY_CSV,
) -> tuple[int, bool]:
    """Seed or validate local inventory without overwriting existing state."""

    root_path = Path(root).resolve()
    database = _relative_local_path(root_path, inventory_path, label="inventory path")
    csv_path = _relative_local_path(root_path, inventory_csv, label="inventory CSV path")
    rows = tuple(jobs)
    if not rows:
        raise ExecutorPreparationError("cannot prepare inventory from an empty plan")
    expected = {str(row["job_id"]): row for row in rows}

    with InventoryStore(database) as store:
        existing = store.list_jobs()
        existing_for_plan = tuple(record for record in existing if record.plan_name == rows[0]["plan_name"])
        existing_by_id = {record.job_id: record for record in existing_for_plan}
        if existing_for_plan:
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


def _job_target(root: Path, job: JobRecord) -> Path:
    directory = _relative_local_path(root, job.output_directory, label="job output directory")
    filename = Path(job.output_filename)
    if filename.is_absolute() or filename.name != job.output_filename:
        raise ExecutorPreparationError(f"job output filename is unsafe: {job.job_id}")
    target = (directory / filename).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ExecutorPreparationError(f"job output path escapes root: {job.job_id}") from exc
    return target


def _partial_target(root: Path, job: JobRecord) -> Path:
    partial_root = _relative_local_path(root, DEFAULT_PARTIAL_DIRECTORY, label="partial directory")
    target = partial_root / job.plan_name / str(job.year) / job.output_filename
    resolved = target.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ExecutorPreparationError(f"partial output path escapes root: {job.job_id}") from exc
    return resolved


def build_subset_kwargs(
    job: JobRecord,
    *,
    aoi: AOIBounds,
    depth_m: float,
    output_directory: str | Path,
) -> dict[str, Any]:
    """Build the explicit Copernicus Marine subset arguments for one job."""

    if job.plan_name == "monthly_all" and job.expected_timesteps == 1:
        end_datetime = job.start_datetime
    elif job.plan_name == "daily_jfm":
        start = datetime.fromisoformat(job.start_datetime)
        end = start + timedelta(days=job.expected_timesteps - 1)
        end_datetime = end.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        end_datetime = job.end_datetime
    return {
        "dataset_id": job.dataset_id,
        "dataset_version": job.dataset_version,
        "dataset_part": job.dataset_part,
        "variables": list(VARIABLES),
        "minimum_longitude": aoi.west,
        "maximum_longitude": aoi.east,
        "minimum_latitude": aoi.south,
        "maximum_latitude": aoi.north,
        "minimum_depth": depth_m,
        "maximum_depth": depth_m,
        "vertical_axis": "depth",
        "start_datetime": job.start_datetime,
        "end_datetime": end_datetime,
        "coordinates_selection_method": "nearest",
        "output_filename": job.output_filename,
        "output_directory": str(output_directory),
        "file_format": "netcdf",
        "overwrite": False,
        "skip_existing": False,
        "netcdf_compression_level": 1,
        "raise_if_updating": True,
    }


def validate_output(path: str | Path, job: JobRecord, *, depth_m: float) -> BasicCheck:
    """Validate a local NetCDF's existence, variables, time count, and depth."""

    target = Path(path)
    if target.is_symlink() or not target.is_file():
        raise DownloadExecutionError(f"output file is missing or not a regular file: {job.job_id}")
    size_bytes = target.stat().st_size
    if size_bytes <= 0:
        raise DownloadExecutionError(f"output file is empty: {job.job_id}")
    try:
        import xarray as xr
    except ImportError as exc:
        raise DownloadExecutionError("xarray is required for NetCDF basic check") from exc

    try:
        with xr.open_dataset(target, decode_times=True) as dataset:
            variables = tuple(sorted(name for name in VARIABLES if name in dataset.data_vars))
            if variables != tuple(sorted(VARIABLES)):
                missing = sorted(set(VARIABLES) - set(variables))
                raise DownloadExecutionError(
                    f"NetCDF is missing required variables: {','.join(missing)}"
                )
            if "time" not in dataset.sizes:
                raise DownloadExecutionError(f"NetCDF has no time dimension: {job.job_id}")
            timestep_count = int(dataset.sizes["time"])
            if timestep_count != job.expected_timesteps:
                raise DownloadExecutionError(
                    f"timestep mismatch for {job.job_id}: "
                    f"expected {job.expected_timesteps}, observed {timestep_count}"
                )
            depth = dataset.coords.get("depth")
            if depth is None:
                depth = dataset.variables.get("depth")
            if depth is None:
                raise DownloadExecutionError(f"NetCDF has no depth coordinate: {job.job_id}")
            values = depth.values
            flat_values = list(values.flat) if hasattr(values, "flat") else [values]
            if len(flat_values) != 1:
                raise DownloadExecutionError(f"NetCDF depth selection is not scalar: {job.job_id}")
            observed_depth = float(flat_values[0])
            if abs(observed_depth - depth_m) > DEPTH_TOLERANCE_M:
                raise DownloadExecutionError(
                    f"depth mismatch for {job.job_id}: expected {depth_m}, observed {observed_depth}"
                )
    except DownloadExecutionError:
        raise
    except Exception as exc:
        raise DownloadExecutionError(f"NetCDF basic check failed for {job.job_id}") from exc
    return BasicCheck(
        size_bytes=size_bytes,
        timestep_count=timestep_count,
        depth_m=observed_depth,
        variables=variables,
    )


def _write_job_log(root: Path, job: JobRecord, event: Mapping[str, Any]) -> None:
    """Write one sanitized JSON job log using atomic replacement."""

    target = root / DEFAULT_LOG_DIRECTORY / f"{job.job_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(render_event(event))
    existing: dict[str, Any] = {"job_id": job.job_id, "events": []}
    if target.exists():
        try:
            candidate = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(candidate, dict) and isinstance(candidate.get("events"), list):
                existing = candidate
        except (OSError, json.JSONDecodeError):
            existing = {"job_id": job.job_id, "events": []}
    existing["events"].append(payload)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{job.job_id}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(existing, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise DownloadExecutionError(f"job log write failed: {job.job_id}") from exc


def _transition_to_downloading(store: InventoryStore, job_id: str) -> JobRecord:
    """Normalize a resumable job into ``downloading``."""

    job = store.get_job(job_id)
    if job is None:
        raise DownloadExecutionError(f"inventory job not found: {job_id}")
    if job.status == "planned":
        job = store.transition(job_id, "preflight_passed")
    if job.status == "failed_retryable":
        job = store.transition(job_id, "retry_wait")
    if job.status in {"preflight_passed", "retry_wait", "quarantined"}:
        job = store.transition(job_id, "downloading", attempt_count=job.attempt_count + 1)
    elif job.status == "downloading":
        job = store.transition(job_id, "downloading", attempt_count=job.attempt_count + 1)
    elif job.status == "failed_permanent":
        raise DownloadExecutionError(f"job requires manual review: {job_id}")
    return job


def _mark_failed_permanent(store: InventoryStore, job_id: str) -> JobRecord:
    """Reach ``failed_permanent`` using only legal state-machine edges."""

    current = store.get_job(job_id)
    if current is None:
        raise DownloadExecutionError(f"inventory job not found: {job_id}")
    if current.status == "failed_permanent":
        return current
    if current.status == "quarantined":
        current = store.transition(job_id, "downloading")
    if current.status == "downloading":
        current = store.transition(job_id, "failed_retryable")
    if current.status == "failed_retryable":
        current = store.transition(job_id, "failed_permanent")
    if current.status != "failed_permanent":
        raise DownloadExecutionError(
            f"cannot mark job permanently failed from status {current.status}: {job_id}"
        )
    return current


def _finish_valid_existing(
    store: InventoryStore,
    job: JobRecord,
    *,
    root: Path,
    target: Path,
    depth_m: float,
) -> JobRecord:
    """Mark an already-valid target as skipped and stage-4 ready."""

    check = validate_output(target, job, depth_m=depth_m)
    digest = sha256_file(target)
    current = store.get_job(job.job_id)
    if current is None:
        raise DownloadExecutionError(f"inventory job disappeared: {job.job_id}")
    if current.status == "planned":
        current = store.transition(job.job_id, "skipped_valid", checksum=digest)
        current = store.transition(job.job_id, "ready_for_stage4", checksum=digest)
    else:
        if current.status in {"preflight_passed", "retry_wait", "failed_retryable", "quarantined"}:
            current = _transition_to_downloading(store, job.job_id)
        if current.status == "downloading":
            current = store.transition(job.job_id, "downloaded")
        if current.status == "downloaded":
            current = store.transition(job.job_id, "basic_check_passed")
        if current.status == "basic_check_passed":
            current = store.transition(job.job_id, "checksum_recorded", checksum=digest)
        if current.status == "checksum_recorded":
            current = store.transition(job.job_id, "ready_for_stage4", checksum=digest)
    _write_job_log(
        root,
        current,
        {
            "job_id": current.job_id,
            "status": current.status,
            "event": "skipped_valid",
            "size_bytes": check.size_bytes,
            "timestep_count": check.timestep_count,
            "checksum": digest,
        },
    )
    return current


def _quarantine_invalid(
    store: InventoryStore,
    job: JobRecord,
    *,
    source: Path,
    root: Path,
    reason: str,
) -> None:
    """Record and quarantine an invalid local output before retrying."""

    current = store.get_job(job.job_id)
    if current is None:
        raise DownloadExecutionError(f"inventory job disappeared: {job.job_id}")
    if current.status in {"planned", "preflight_passed", "retry_wait", "failed_retryable", "quarantined"}:
        current = _transition_to_downloading(store, job.job_id)
    if current.status == "downloading":
        current = store.transition(job.job_id, "downloaded")
    if current.status == "downloaded":
        quarantine_file(
            source,
            root=root,
            job_id=job.job_id,
            reason=reason,
        )
        store.transition(job.job_id, "quarantined")


def _atomic_move(source: Path, target: Path, *, job_id: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise DownloadExecutionError(f"target already exists and will not be overwritten: {job_id}")
    try:
        os.rename(source, target)
    except OSError as exc:
        raise DownloadExecutionError(f"atomic move failed: {job_id}") from exc


def execute_plan(
    root: str | Path,
    plan_name: str,
    *,
    inventory_path: str | Path = DEFAULT_INVENTORY_PATH,
    inventory_csv: str | Path = DEFAULT_INVENTORY_CSV,
    backoff_policy: BackoffPolicy = DEFAULT_BACKOFF_POLICY,
    subset_callable: Callable[..., Any] | None = None,
    sleep_callable: Callable[[float], None] = time.sleep,
    job_id: str | None = None,
    force_after_quarantine: bool = False,
) -> PlanSummary:
    """Execute one approved plan using Copernicus Marine's local session.

    This function is intentionally not called unless the CLI receives
    ``--execute``.  Tests inject ``subset_callable`` and never make a request.
    """

    root_path = Path(root).resolve()
    aoi, depth_m = load_runtime_config(root_path)
    jobs, summary = build_local_plan(root_path, plan_name)
    prepare_inventory(
        root_path,
        jobs,
        inventory_path=inventory_path,
        inventory_csv=inventory_csv,
    )
    database = _relative_local_path(root_path, inventory_path, label="inventory path")
    if subset_callable is None:
        try:
            import copernicusmarine
        except ImportError as exc:
            raise DownloadExecutionError("copernicusmarine is not installed in this environment") from exc
        subset_callable = copernicusmarine.subset

    failures: list[str] = []
    with InventoryStore(database) as store:
        if force_after_quarantine:
            if not job_id:
                raise BatchExecutionError(
                    "--force-after-quarantine requires --job-id"
                )
            forced_job = store.get_job(job_id)
            if forced_job is None:
                raise BatchExecutionError(f"job not found for manual retry: {job_id}")
            if forced_job.status != "failed_permanent":
                raise BatchExecutionError(
                    f"manual retry requires failed_permanent status: {job_id}"
                )
            target = _job_target(root_path, forced_job)
            quarantine_root = root_path / "data" / "quarantine"
            quarantined = tuple(
                quarantine_root.rglob(forced_job.output_filename)
                if quarantine_root.exists()
                else ()
            )
            if target.exists() or not quarantined:
                raise BatchExecutionError(
                    f"manual retry requires a quarantined output and no active target: {job_id}"
                )
            store.requeue_failed_permanent(
                job_id,
                reason="manual retry after corrected executor boundary handling",
            )

        selected_jobs = tuple(job for job in store.list_jobs() if job.plan_name == plan_name)
        if job_id:
            selected = store.get_job(job_id)
            if selected is None:
                raise BatchExecutionError(f"job not found: {job_id}")
            selected_jobs = (selected,)
        for initial_job in selected_jobs:
            job = store.get_job(initial_job.job_id)
            if job is None or job.status in {"ready_for_stage4", "skipped_valid"}:
                continue
            if job.status == "failed_permanent":
                raise BatchExecutionError(f"manual review required before resuming: {job.job_id}")

            target = _job_target(root_path, job)
            partial = _partial_target(root_path, job)
            if target.exists():
                try:
                    _finish_valid_existing(
                        store,
                        job,
                        root=root_path,
                        target=target,
                        depth_m=depth_m,
                    )
                    continue
                except DownloadExecutionError:
                    _quarantine_invalid(
                        store,
                        job,
                        source=target,
                        root=root_path,
                        reason="existing target failed basic check before download",
                    )
                    job = store.get_job(job.job_id)
            if partial.exists():
                _quarantine_invalid(
                    store,
                    job,
                    source=partial,
                    root=root_path,
                    reason="partial output found before download attempt",
                )

            while True:
                job = _transition_to_downloading(store, job.job_id)
                try:
                    partial.parent.mkdir(parents=True, exist_ok=True)
                    response = subset_callable(
                        **build_subset_kwargs(
                            job,
                            aoi=aoi,
                            depth_m=depth_m,
                            output_directory=partial.parent,
                        )
                    )
                    if not partial.exists():
                        raise DownloadExecutionError(
                            f"Copernicus response produced no output file: {job.job_id}"
                        )
                    check = validate_output(partial, job, depth_m=depth_m)
                    _atomic_move(partial, target, job_id=job.job_id)
                    job = store.transition(job.job_id, "downloaded")
                    job = store.transition(job.job_id, "basic_check_passed")
                    digest = sha256_file(target)
                    job = store.transition(job.job_id, "checksum_recorded", checksum=digest)
                    job = store.transition(job.job_id, "ready_for_stage4", checksum=digest)
                    _write_job_log(
                        root_path,
                        job,
                        {
                            "job_id": job.job_id,
                            "status": job.status,
                            "event": "downloaded",
                            "attempt": job.attempt_count,
                            "response_type": type(response).__name__,
                            "size_bytes": check.size_bytes,
                            "timestep_count": check.timestep_count,
                            "checksum": digest,
                        },
                    )
                    break
                except Exception as error:
                    decision = classify_error(error)
                    current = store.get_job(job.job_id)
                    if current is None:
                        raise BatchExecutionError(f"inventory job disappeared: {job.job_id}") from error
                    if partial.exists():
                        try:
                            _quarantine_invalid(
                                store,
                                current,
                                source=partial,
                                root=root_path,
                                reason="download attempt produced an invalid or partial file",
                            )
                            current = store.get_job(job.job_id)
                        except Exception as quarantine_error:
                            _write_job_log(
                                root_path,
                                current,
                                {
                                    "job_id": current.job_id,
                                    "status": current.status,
                                    "event": "quarantine_failed",
                                    "error": sanitize_exception(quarantine_error),
                                },
                            )
                            raise BatchExecutionError(
                                f"cannot quarantine failed output: {job.job_id}"
                            ) from quarantine_error
                    _write_job_log(
                        root_path,
                        current,
                        {
                            "job_id": current.job_id,
                            "status": current.status,
                            "event": "download_error",
                            "attempt": current.attempt_count,
                            "decision": decision.value,
                            "error": sanitize_exception(error),
                        },
                    )
                    if decision is RetryDecision.RETRYABLE and backoff_policy.can_retry(current.attempt_count):
                        if current.status == "quarantined":
                            current = store.transition(current.job_id, "downloading")
                        if current.status == "downloading":
                            current = store.transition(current.job_id, "failed_retryable")
                        if current.status == "failed_retryable":
                            current = store.transition(current.job_id, "retry_wait")
                        delay = backoff_policy.delay_for_attempt(current.attempt_count)
                        _write_job_log(
                            root_path,
                            current,
                            {
                                "job_id": current.job_id,
                                "status": current.status,
                                "event": "retry_wait",
                                "delay_seconds": delay,
                            },
                        )
                        sleep_callable(delay)
                        job = current
                        continue
                    current = _mark_failed_permanent(store, current.job_id)
                    failures.append(current.job_id)
                    raise BatchExecutionError(
                        f"batch stopped on permanent failure: {current.job_id}"
                    ) from error
    if failures:
        raise BatchExecutionError(f"batch finished with failures: {','.join(failures)}")
    return summary


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
        "--execute",
        action="store_true",
        help="perform the remote Copernicus subset operation; requires explicit opt-in",
    )
    parser.add_argument(
        "--prepare-inventory",
        action="store_true",
        help="seed/validate local SQLite and CSV inventory; only with --dry-run",
    )
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--inventory-csv", type=Path, default=DEFAULT_INVENTORY_CSV)
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_BACKOFF_POLICY.max_attempts)
    parser.add_argument("--job-id", type=str)
    parser.add_argument("--force-after-quarantine", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.dry_run and args.execute:
        print("error=--dry-run and --execute are mutually exclusive")
        return 2
    if args.prepare_inventory and not args.dry_run:
        print("error=--prepare-inventory requires --dry-run")
        return 2
    if args.max_attempts < 1:
        print("error=--max-attempts must be positive")
        return 2
    if args.force_after_quarantine and not args.execute:
        print("error=--force-after-quarantine requires --execute")
        return 2
    try:
        jobs, summary = build_local_plan(args.root, args.plan)
        print("stage=T3-014")
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
        if args.dry_run:
            load_runtime_config(args.root)
            print("authentication=NOT_PERFORMED")
            print("network=NOT_PERFORMED")
            print("download=NOT_PERFORMED")
            print("status=DRY_RUN_READY")
            return 0
        if not args.execute:
            raise ExecutionDisabledError(
                "actual T3-014 download requires explicit --execute; "
                "network and authentication are never implicit"
            )
        policy = BackoffPolicy(max_attempts=args.max_attempts)
        execute_plan(
            args.root,
            args.plan,
            inventory_path=args.inventory,
            inventory_csv=args.inventory_csv,
            backoff_policy=policy,
            job_id=args.job_id,
            force_after_quarantine=args.force_after_quarantine,
        )
        print("authentication=DELEGATED_TO_LOCAL_COPERNICUS_TOOL")
        print("network=PERFORMED_BY_EXECUTE_MODE")
        print("download=COMPLETED")
        print("status=EXECUTION_COMPLETE")
        return 0
    except ExecutionDisabledError as exc:
        print(f"error={exc}")
        return 3
    except (PlanError, ExecutorPreparationError) as exc:
        print(f"error={exc}")
        return 2
    except (DownloadExecutionError, BatchExecutionError, OSError, ValueError) as exc:
        print(f"error={exc}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
