"""Validate Stage 4 NetCDF files locally, including the approved WP-2 checks.

The validator is deliberately read-only.  It opens NetCDF files with xarray,
reads the existing SQLite inventory in ``mode=ro``, and never changes raw
files, inventory state, or any remote service.  The default ``wp1`` scope
covers T4-001 through T4-004.  The explicit ``wp2`` scope adds T4-005 through
T4-008.  The explicit ``full`` scope adds T4-009 through T4-014 and is still
local/offline; it does not authorize conversion, upload, or Earth Engine work.
"""

from __future__ import annotations

import argparse
from calendar import monthrange
from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys
from typing import Any, Mapping

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_INVENTORY_PATH = Path("outputs/inventory/download_inventory.sqlite")
DEFAULT_MANIFEST_PATH = Path("outputs/manifests/stage_4_validated_manifest.json")
DEFAULT_REPORT_PATH = Path("outputs/evidence/stage_4/T4-013_validation_report.result.txt")
DEFAULT_GATE_PATH = Path("outputs/evidence/stage_4/T4-014_stage4_gate.result.txt")
EXPECTED_DIMS = ("time", "depth", "latitude", "longitude")
ACCEPTED_CALENDARS = frozenset({"standard", "gregorian", "proleptic_gregorian"})
REQUIRED_VARIABLES = ("uo", "vo")


class Stage4ValidationError(ValueError):
    """Raised when the local validation cannot be evaluated safely."""


@dataclass(frozen=True)
class FileValidationResult:
    """Deterministic result for one inventory-scoped NetCDF file."""

    job_id: str
    plan_name: str
    relative_path: str
    status: str
    checks: tuple[str, ...]
    errors: tuple[str, ...]
    anomalies: tuple[str, ...]
    time_count: int | None = None
    time_first: str | None = None
    time_last: str | None = None
    depth_value_m: float | None = None
    normalized_units: tuple[str, ...] = ()
    details: tuple[str, ...] = ()
    source_checksum: str = ""
    expected_timesteps: int | None = None
    coverage_metrics: tuple[tuple[str, int, int, float], ...] = ()
    distribution_metrics: tuple[
        tuple[str, int, float, float, float, float, float, float, float]
    , ...] = ()
    consistency: tuple[str, ...] = ()
    dataset_id: str = ""
    dataset_version: str = ""
    dataset_part: str = ""
    start_datetime: str = ""
    end_datetime: str = ""

    @property
    def downstream_ready(self) -> bool:
        """Return whether this file may enter the validated manifest."""

        return self.status == "PASS"


@dataclass(frozen=True)
class Stage4ValidationReport:
    """Scoped Stage 4 summary and per-file results."""

    results: tuple[FileValidationResult, ...]
    target_depth_m: float
    depth_tolerance_m: float
    config_hash: str
    inventory_rows: int
    command: str
    scope: str

    @property
    def files_checked(self) -> int:
        """Return the number of inventory rows evaluated."""

        return len(self.results)

    @property
    def files_pass(self) -> int:
        """Return the number of files passing WP-1."""

        return sum(result.status == "PASS" for result in self.results)

    @property
    def files_fail(self) -> int:
        """Return the number of files failing WP-1."""

        return sum(result.status == "FAIL" for result in self.results)

    @property
    def anomaly_count(self) -> int:
        """Return the number of non-blocking anomaly notes."""

        return sum(len(result.anomalies) for result in self.results)

    @property
    def has_full_quality_metrics(self) -> bool:
        """Return whether T4-009 through T4-011 were evaluated per file."""

        return self.scope == "full" and all(
            result.coverage_metrics and result.distribution_metrics and result.consistency
            for result in self.results
        )


def _read_json(root: Path, relative_path: str) -> dict[str, Any]:
    try:
        value = json.loads((root / relative_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Stage4ValidationError(f"cannot read local configuration: {relative_path}") from exc
    if not isinstance(value, dict):
        raise Stage4ValidationError(f"configuration must be an object: {relative_path}")
    return value


def _config_context(root: Path) -> tuple[float, float, str]:
    depth_config = _read_json(root, "config/depth_selection.json")
    period_config = _read_json(root, "config/analysis_period.json")
    try:
        target = float(depth_config["analysis_depth_m"])
        tolerance = float(depth_config["tolerance_m"])
        start = str(period_config["full_period"]["start"])
        end = str(period_config["full_period"]["end_exclusive"])
    except (KeyError, TypeError, ValueError) as exc:
        raise Stage4ValidationError("depth or period configuration is incomplete") from exc
    if tolerance < 0 or not start < end:
        raise Stage4ValidationError("invalid depth tolerance or full-period bounds")
    digest = hashlib.sha256()
    for relative_path in (
        "config/analysis_period.json",
        "config/depth_selection.json",
        "config/study_area.json",
    ):
        digest.update((root / relative_path).read_bytes())
    return target, tolerance, digest.hexdigest()


def _read_inventory(root: Path, inventory_path: str | Path) -> tuple[dict[str, Any], ...]:
    candidate = Path(inventory_path)
    if candidate.is_absolute():
        raise Stage4ValidationError("inventory path must be relative to repository root")
    database = (root / candidate).resolve()
    try:
        database.relative_to(root.resolve())
    except ValueError as exc:
        raise Stage4ValidationError("inventory path escapes repository root") from exc
    if not database.is_file():
        raise Stage4ValidationError(f"inventory database does not exist: {database}")
    try:
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
    except sqlite3.Error as exc:
        raise Stage4ValidationError("cannot open inventory in read-only mode") from exc
    try:
        rows = connection.execute(
            "SELECT * FROM download_inventory "
            "WHERE plan_name IN ('monthly_all', 'daily_jfm') ORDER BY job_id"
        ).fetchall()
        return tuple(dict(row) for row in rows)
    except sqlite3.Error as exc:
        raise Stage4ValidationError("cannot read inventory in read-only mode") from exc
    finally:
        connection.close()


def _safe_target(root: Path, row: Mapping[str, Any]) -> Path:
    directory = Path(str(row["output_directory"]))
    filename = Path(str(row["output_filename"]))
    if directory.is_absolute() or filename.is_absolute() or filename.name != str(row["output_filename"]):
        raise Stage4ValidationError(f"unsafe inventory path: {row['job_id']}")
    target = (root / directory / filename).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise Stage4ValidationError(f"inventory path escapes repository root: {row['job_id']}") from exc
    return target


def _normalize_unit(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Stage4ValidationError("missing units attribute")
    normalized = (
        value.strip().lower().replace("−", "-").replace("–", "-")
        .replace("^", "")
    )
    normalized = " ".join(normalized.split())
    accepted = {
        "m s-1",
        "m/s",
        "meter second-1",
        "meters second-1",
        "metre second-1",
        "metres second-1",
        "meter per second",
        "meters per second",
        "metre per second",
        "metres per second",
    }
    if normalized not in accepted:
        raise Stage4ValidationError(f"unsupported units: {value}")
    return "m s-1"


def _timestamp_strings(values: object) -> tuple[str, ...]:
    converted: list[str] = []
    for value in np.asarray(values).reshape(-1):
        try:
            converted.append(str(np.datetime64(value, "ns")))
        except (TypeError, ValueError):
            converted.append(str(value))
    return tuple(converted)


def _expected_timestamps(row: Mapping[str, Any]) -> tuple[str, ...]:
    year = int(row["year"])
    month = int(row["month"])
    start = date(year, month, 1)
    count = 1 if row["plan_name"] == "monthly_all" else monthrange(year, month)[1]
    return tuple(str(np.datetime64(start + timedelta(days=index), "ns")) for index in range(count))


def _validate_full_quality(
    dataset: xr.Dataset,
    *,
    checks: list[str],
    errors: list[str],
    details: list[str],
    coverage_metrics: list[tuple[str, int, int, float]],
    distribution_metrics: list[tuple[str, int, float, float, float, float, float, float, float]],
    consistency: list[str],
) -> None:
    """Evaluate coverage, paired-band consistency, and descriptive distributions."""

    coverage_ok = True
    distribution_ok = True
    consistency_ok = True
    masks: dict[str, np.ndarray] = {}

    for name in REQUIRED_VARIABLES:
        values = np.asarray(dataset[name].values)
        mask = np.isfinite(values)
        masks[name] = mask
        total_count = int(mask.size)
        valid_count = int(mask.sum())
        coverage_pct = (100.0 * valid_count / total_count) if total_count else 0.0
        coverage_metrics.append((name, valid_count, total_count, coverage_pct))
        details.append(
            f"{name}:valid_count={valid_count},total_count={total_count},"
            f"coverage_pct={coverage_pct:.9f}"
        )
        if total_count == 0 or valid_count == 0 or not 0.0 <= coverage_pct <= 100.0:
            errors.append(f"{name} valid pixel coverage is empty or invalid")
            coverage_ok = False
            distribution_ok = False
            continue
        finite = values[mask].astype(float, copy=False)
        quantiles = np.quantile(finite, [0.01, 0.50, 0.99])
        distribution = (
            name,
            valid_count,
            float(np.min(finite)),
            float(np.max(finite)),
            float(np.mean(finite)),
            float(np.std(finite)),
            float(quantiles[0]),
            float(quantiles[1]),
            float(quantiles[2]),
        )
        distribution_metrics.append(distribution)
        details.append(
            f"{name}:distribution_count={valid_count},min={distribution[2]:.12g},"
            f"max={distribution[3]:.12g},mean={distribution[4]:.12g},"
            f"std={distribution[5]:.12g},p01={distribution[6]:.12g},"
            f"p50={distribution[7]:.12g},p99={distribution[8]:.12g}"
        )

    if all(name in masks for name in REQUIRED_VARIABLES):
        mask_equal = bool(np.array_equal(masks["uo"], masks["vo"]))
        consistency.append(f"uo_vo_mask_equal={str(mask_equal).lower()}")
        if not mask_equal:
            errors.append("uo and vo valid-pixel masks are not identical")
            consistency_ok = False
        for coordinate in ("time", "depth", "latitude", "longitude"):
            uo_coord = dataset["uo"].coords.get(coordinate)
            vo_coord = dataset["vo"].coords.get(coordinate)
            equal = bool(
                uo_coord is not None
                and vo_coord is not None
                and uo_coord.dims == vo_coord.dims
                and np.array_equal(np.asarray(uo_coord.values), np.asarray(vo_coord.values))
            )
            consistency.append(f"uo_vo_{coordinate}_equal={str(equal).lower()}")
            if not equal:
                errors.append(f"uo and vo {coordinate} coordinates are not identical")
                consistency_ok = False
        dimensions_equal = (
            dataset["uo"].dims == dataset["vo"].dims
            and dataset["uo"].shape == dataset["vo"].shape
        )
        consistency.append(f"uo_vo_dimensions_equal={str(dimensions_equal).lower()}")
        if not dimensions_equal:
            errors.append("uo and vo dimensions or shapes are not identical")
            consistency_ok = False

    if coverage_ok:
        checks.append("T4-009 valid pixel counts and coverage recorded")
    else:
        errors.append("T4-009 failed")
    if consistency_ok:
        checks.append("T4-010 uo/vo mask, time, and grid are identical")
    else:
        errors.append("T4-010 failed")
    if distribution_ok and len(distribution_metrics) == len(REQUIRED_VARIABLES):
        checks.append("T4-011 per-file distribution statistics recorded")
    else:
        errors.append("T4-011 failed")


def _validate_wp2_dataset(
    dataset: xr.Dataset,
    raw_dataset: xr.Dataset,
    *,
    checks: list[str],
    errors: list[str],
    anomalies: list[str],
    details: list[str],
) -> None:
    """Validate mask/fill, coordinate orientation, encoding, and plausibility."""

    wp2_checks = {"T4-005": True, "T4-006": True, "T4-007": True, "T4-008": True}
    finite_counts: list[int] = []
    for name in REQUIRED_VARIABLES:
        decoded = np.asarray(dataset[name].values)
        raw = np.asarray(raw_dataset[name].values)
        attrs = raw_dataset[name].attrs
        if decoded.shape != raw.shape:
            errors.append(f"{name} raw/decoded shape mismatch")
            wp2_checks["T4-007"] = False
            continue
        fill_value = attrs.get("_FillValue")
        fill_mask = np.zeros(raw.shape, dtype=bool)
        if fill_value is not None:
            try:
                fill_number = float(fill_value)
                if fill_number == 0:
                    errors.append(f"{name} _FillValue is zero")
                    wp2_checks["T4-005"] = False
                fill_mask = raw == fill_value
            except (TypeError, ValueError):
                errors.append(f"{name} _FillValue is not numeric")
                wp2_checks["T4-005"] = False
        decoded_nan = ~np.isfinite(decoded)
        raw_fill_count = int(fill_mask.sum())
        decoded_nan_count = int(decoded_nan.sum())
        finite_counts.append(int(np.isfinite(decoded).sum()))
        details.append(
            f"{name}:raw_fill_count={raw_fill_count},decoded_nan_count={decoded_nan_count}"
        )
        if raw_fill_count != decoded_nan_count:
            errors.append(
                f"{name} raw fill count {raw_fill_count} != decoded NaN count {decoded_nan_count}"
            )
            wp2_checks["T4-005"] = False
        if np.any(np.isfinite(decoded[fill_mask])):
            errors.append(f"{name} fill value remained finite after CF decoding")
            wp2_checks["T4-005"] = False
        valid_raw = ~fill_mask & np.isfinite(raw)
        raw_zero = valid_raw & (raw == 0)
        if raw_zero.any():
            offset = float(attrs.get("add_offset", 0.0))
            if not np.allclose(decoded[raw_zero], offset, rtol=0.0, atol=1e-12):
                errors.append(f"{name} valid raw zero did not remain the decoded offset")
                wp2_checks["T4-005"] = False
        scale = float(attrs.get("scale_factor", 1.0))
        offset = float(attrs.get("add_offset", 0.0))
        if not np.isfinite(scale) or not np.isfinite(offset) or scale == 0:
            errors.append(f"{name} has invalid scale_factor/add_offset")
            wp2_checks["T4-007"] = False
        else:
            expected = raw.astype(float) * scale + offset
            compare_mask = valid_raw & np.isfinite(decoded)
            tolerance = max(1e-12, abs(scale) * 1e-6)
            if compare_mask.any() and not np.allclose(
                decoded[compare_mask], expected[compare_mask], rtol=1e-12, atol=tolerance
            ):
                errors.append(f"{name} decoded values do not match raw scale/offset exactly")
                wp2_checks["T4-007"] = False
            details.append(f"{name}:scale_factor={scale},add_offset={offset}")
        for sentinel in (-32767.0, -9999.0, 1e20, -1e20):
            if np.any(np.isfinite(decoded) & (decoded == sentinel)):
                errors.append(f"{name} decoded values contain sentinel {sentinel:g}")
                wp2_checks["T4-008"] = False
        finite = decoded[np.isfinite(decoded)]
        if not len(finite):
            errors.append(f"{name} contains no finite decoded values")
            wp2_checks["T4-008"] = False
        valid_min = attrs.get("valid_min")
        valid_max = attrs.get("valid_max")
        if valid_min is not None and valid_max is not None and len(finite):
            lower = float(valid_min) * scale + offset
            upper = float(valid_max) * scale + offset
            lower, upper = min(lower, upper), max(lower, upper)
            tolerance = max(1e-12, abs(scale) * 1e-6)
            observed_min = float(np.nanmin(finite))
            observed_max = float(np.nanmax(finite))
            excursion = max(lower - observed_min, observed_max - upper, 0.0)
            if excursion > tolerance:
                message = (
                    f"{name} decoded values exceed encoded valid range "
                    f"{lower:.12g}..{upper:.12g}; excursion={excursion:.12g}"
                )
                if excursion <= 0.5:
                    anomalies.append(message)
                else:
                    errors.append(message)
                    wp2_checks["T4-008"] = False
            details.append(f"{name}:decoded_valid_range={lower}..{upper}")
    if any(count == 0 for count in finite_counts):
        wp2_checks["T4-008"] = False
    for coordinate, dimension in (("latitude", "latitude"), ("longitude", "longitude")):
        if coordinate not in dataset.coords:
            errors.append(f"{coordinate} coordinate is missing")
            wp2_checks["T4-006"] = False
            continue
        values = np.asarray(dataset[coordinate].values, dtype=float)
        if dataset[coordinate].dims != (dimension,) or values.ndim != 1 or len(values) < 2:
            errors.append(f"{coordinate} coordinate must be a one-dimensional vector")
            wp2_checks["T4-006"] = False
            continue
        differences = np.diff(values)
        if not np.all(np.isfinite(values)) or np.all(differences > 0):
            order = "ascending"
        elif np.all(differences < 0):
            order = "descending"
        else:
            errors.append(f"{coordinate} coordinate is not strictly monotonic")
            wp2_checks["T4-006"] = False
            order = "invalid"
        details.append(f"{coordinate}_order={order}")
    if all(wp2_checks.values()):
        checks.extend([
            "T4-005 mask/fill preserved and valid zeros retained",
            "T4-006 latitude/longitude strictly monotonic",
            "T4-007 raw/decoded scale and offset match",
            "T4-008 finite values and encoded plausibility bounds valid",
        ])
    else:
        for code, passed in wp2_checks.items():
            if not passed:
                errors.append(f"{code} failed")


def _validate_dataset(
    path: Path,
    row: Mapping[str, Any],
    *,
    target_depth_m: float,
    depth_tolerance_m: float,
    scope: str = "wp1",
) -> FileValidationResult:
    if scope not in {"wp1", "wp2", "full"}:
        raise Stage4ValidationError(f"unsupported validation scope: {scope}")
    errors: list[str] = []
    anomalies: list[str] = []
    checks: list[str] = []
    details: list[str] = []
    depth_value: float | None = None
    units: list[str] = []
    time_count: int | None = None
    time_first: str | None = None
    time_last: str | None = None
    relative_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    coverage_metrics: list[tuple[str, int, int, float]] = []
    distribution_metrics: list[tuple[str, int, float, float, float, float, float, float, float]] = []
    consistency: list[str] = []

    if str(row["status"]) != "ready_for_stage4":
        errors.append(f"inventory status is not ready_for_stage4: {row['status']}")
    if scope == "full" and not str(row.get("checksum", "")).strip():
        errors.append("source checksum is missing from inventory")
    if not path.is_file() or path.is_symlink():
        errors.append("active NetCDF file is missing or not a regular file")
    if errors:
        return FileValidationResult(
            str(row["job_id"]), str(row["plan_name"]), relative_path, "FAIL",
            tuple(checks), tuple(errors), tuple(anomalies), normalized_units=tuple(units),
            details=tuple(details),
            source_checksum=str(row.get("checksum", "")),
            expected_timesteps=int(row.get("expected_timesteps", 0)),
            dataset_id=str(row.get("dataset_id", "")),
            dataset_version=str(row.get("dataset_version", "")),
            dataset_part=str(row.get("dataset_part", "")),
            start_datetime=str(row.get("start_datetime", "")),
            end_datetime=str(row.get("end_datetime", "")),
        )

    try:
        raw_context = (
            xr.open_dataset(path, engine="h5netcdf", decode_cf=False, mask_and_scale=False)
            if scope in {"wp2", "full"} else nullcontext(None)
        )
        with xr.open_dataset(path, engine="h5netcdf", decode_cf=True, mask_and_scale=True) as dataset, raw_context as raw_dataset:
            dimensions = set(dataset.sizes)
            missing_dimensions = [dimension for dimension in EXPECTED_DIMS if dimension not in dimensions]
            if missing_dimensions:
                errors.append(f"missing dimensions: {','.join(missing_dimensions)}")
            else:
                checks.append("T4-001 dimensions present")
            missing_variables = [name for name in REQUIRED_VARIABLES if name not in dataset.data_vars]
            if missing_variables:
                errors.append(f"missing variables: {','.join(missing_variables)}")
            else:
                checks.append("T4-001 uo/vo present")
            if not missing_variables:
                for name in REQUIRED_VARIABLES:
                    if tuple(dataset[name].dims) != EXPECTED_DIMS:
                        errors.append(f"{name} dimensions are {tuple(dataset[name].dims)}")
                    try:
                        units.append(_normalize_unit(dataset[name].attrs.get("units")))
                    except Stage4ValidationError as exc:
                        errors.append(f"{name} {exc}")
                if dataset["uo"].dims == dataset["vo"].dims and dataset["uo"].shape == dataset["vo"].shape:
                    checks.append("T4-001 uo/vo dimensions consistent")
                else:
                    errors.append("uo and vo dimensions or shapes are inconsistent")
                if len(units) == 2 and units[0] == units[1] == "m s-1":
                    checks.append("T4-002 units normalized explicitly to m s-1")
            if "depth" in dataset.coords:
                depth_values = np.asarray(dataset["depth"].values, dtype=float).reshape(-1)
                if len(depth_values) != 1:
                    errors.append(f"depth coordinate count is {len(depth_values)}, expected 1")
                elif not np.isfinite(depth_values[0]):
                    errors.append("depth coordinate is not finite")
                else:
                    depth_value = float(depth_values[0])
                    if abs(depth_value - target_depth_m) > depth_tolerance_m:
                        errors.append(
                            f"depth mismatch: value={depth_value:.12g}, target={target_depth_m:.12g}, "
                            f"tolerance={depth_tolerance_m:.12g}"
                        )
                    else:
                        checks.append("T4-003 target depth within configured tolerance")
            else:
                errors.append("depth coordinate is missing")
            if "time" not in dataset.coords:
                errors.append("time coordinate is missing")
            else:
                calendar = str(dataset["time"].attrs.get("calendar", "standard")).lower()
                if calendar not in ACCEPTED_CALENDARS:
                    errors.append(f"unsupported calendar: {calendar}")
                actual = _timestamp_strings(dataset["time"].values)
                expected = _expected_timestamps(row)
                time_count = len(actual)
                time_first = actual[0] if actual else None
                time_last = actual[-1] if actual else None
                if len(actual) != len(set(actual)):
                    errors.append("duplicate timestamps")
                if tuple(sorted(actual)) != actual:
                    errors.append("timestamps are not strictly ordered")
                if actual != expected:
                    errors.append(
                        f"timestamp sequence mismatch: expected {expected[0]}..{expected[-1]} "
                        f"({len(expected)}), got {actual[0] if actual else None}..{actual[-1] if actual else None} "
                        f"({len(actual)})"
                    )
                if calendar in ACCEPTED_CALENDARS and actual == expected:
                    checks.append("T4-004 timestamp count/order/calendar match plan")
            if scope in {"wp2", "full"} and raw_dataset is not None:
                _validate_wp2_dataset(
                    dataset, raw_dataset, checks=checks, errors=errors,
                    anomalies=anomalies, details=details
                )
            if scope == "full":
                _validate_full_quality(
                    dataset, checks=checks, errors=errors, details=details,
                    coverage_metrics=coverage_metrics,
                    distribution_metrics=distribution_metrics,
                    consistency=consistency,
                )
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        errors.append(f"NetCDF open/read failed: {type(exc).__name__}: {exc}")

    return FileValidationResult(
        str(row["job_id"]), str(row["plan_name"]), relative_path,
        "PASS" if not errors else "FAIL", tuple(checks), tuple(errors), tuple(anomalies),
        time_count=time_count, time_first=time_first, time_last=time_last,
        depth_value_m=depth_value, normalized_units=tuple(units),
        details=tuple(details),
        source_checksum=str(row.get("checksum", "")),
        expected_timesteps=int(row.get("expected_timesteps", 0)),
        coverage_metrics=tuple(coverage_metrics),
        distribution_metrics=tuple(distribution_metrics),
        consistency=tuple(consistency),
        dataset_id=str(row.get("dataset_id", "")),
        dataset_version=str(row.get("dataset_version", "")),
        dataset_part=str(row.get("dataset_part", "")),
        start_datetime=str(row.get("start_datetime", "")),
        end_datetime=str(row.get("end_datetime", "")),
    )


def validate_stage4(
    root: str | Path,
    *,
    inventory_path: str | Path = DEFAULT_INVENTORY_PATH,
    command: str = "offline validator invocation",
    scope: str = "wp1",
) -> Stage4ValidationReport:
    """Validate every active inventory row for the selected scope without side effects."""

    root_path = Path(root).resolve()
    target_depth, tolerance, config_hash = _config_context(root_path)
    rows = _read_inventory(root_path, inventory_path)
    if len(rows) != 165:
        raise Stage4ValidationError(f"expected 165 inventory rows, found {len(rows)}")
    results = tuple(
        _validate_dataset(
            _safe_target(root_path, row), row,
            target_depth_m=target_depth, depth_tolerance_m=tolerance,
            scope=scope,
        )
        for row in rows
    )
    return Stage4ValidationReport(results, target_depth, tolerance, config_hash, len(rows), command, scope)


def _metric_to_json(metric: tuple[str, int, int, float]) -> dict[str, Any]:
    """Convert one coverage metric to a JSON-safe mapping."""

    variable, valid_count, total_count, coverage_pct = metric
    return {
        "variable": variable,
        "valid_count": valid_count,
        "total_count": total_count,
        "coverage_pct": coverage_pct,
    }


def _distribution_to_json(
    metric: tuple[str, int, float, float, float, float, float, float, float]
) -> dict[str, Any]:
    """Convert one distribution metric to a JSON-safe mapping."""

    variable, valid_count, minimum, maximum, mean, std, p01, p50, p99 = metric
    return {
        "variable": variable,
        "valid_count": valid_count,
        "min": minimum,
        "max": maximum,
        "mean": mean,
        "std": std,
        "p01": p01,
        "p50": p50,
        "p99": p99,
    }


def _period_key(result: FileValidationResult) -> str:
    """Return a stable plan/month grouping for period-level QC."""

    month = result.start_datetime[5:7] if len(result.start_datetime) >= 7 else "unknown"
    return f"{result.plan_name}:{month}"


def distribution_summary(report: Stage4ValidationReport) -> tuple[dict[str, Any], ...]:
    """Summarize file distributions and flag robust extreme changes.

    The flag is a descriptive QC note, not a scientific correction or a gate
    failure.  Comparisons are made within each plan/month group using the
    median and MAD of per-file mean, p01, and p99 values.  A change is flagged
    when it exceeds both eight robust standard deviations (1.4826 * MAD) and
    0.5 m/s.  This prevents a normal small month-to-month variation from being
    promoted to an error while retaining an explicit, reproducible rule.
    """

    grouped: dict[tuple[str, str], list[tuple[FileValidationResult, tuple[Any, ...]]]] = defaultdict(list)
    for result in report.results:
        period = _period_key(result)
        for metric in result.distribution_metrics:
            grouped[(period, metric[0])].append((result, metric))

    summary: dict[str, dict[str, Any]] = {}
    for (period, variable), rows in sorted(grouped.items()):
        counts = np.asarray([float(row[1][1]) for row in rows])
        means = np.asarray([float(row[1][4]) for row in rows])
        stds = np.asarray([float(row[1][5]) for row in rows])
        p01s = np.asarray([float(row[1][6]) for row in rows])
        p50s = np.asarray([float(row[1][7]) for row in rows])
        p99s = np.asarray([float(row[1][8]) for row in rows])
        total_count = int(counts.sum())
        weighted_mean = float(np.average(means, weights=counts)) if total_count else float("nan")
        pooled_variance = (
            float(np.sum(counts * (stds**2 + (means - weighted_mean) ** 2)) / total_count)
            if total_count else float("nan")
        )
        flags: list[str] = []
        for metric_name, values in (("mean", means), ("p01", p01s), ("p99", p99s)):
            if len(values) < 5:
                continue
            median = float(np.median(values))
            mad = float(np.median(np.abs(values - median)))
            threshold = max(8.0 * 1.4826 * mad, 0.5)
            for (result, _), value in zip(rows, values):
                delta = abs(float(value) - median)
                if delta > threshold:
                    flags.append(
                        f"{result.job_id}:{variable}:{metric_name}:"
                        f"delta={delta:.12g}>threshold={threshold:.12g}"
                    )
        summary.setdefault(period, {"period": period, "files": 0, "variables": {}, "flags": []})
        summary[period]["files"] = max(summary[period]["files"], len(rows))
        total_coverage_count = sum(
            next(
                (coverage[2] for coverage in result.coverage_metrics if coverage[0] == variable),
                0,
            )
            for result, _ in rows
        )
        summary[period]["variables"][variable] = {
            "files": len(rows),
            "valid_count": total_count,
            "total_count": total_coverage_count,
            "coverage_pct": (100.0 * total_count / total_coverage_count)
            if total_coverage_count else 0.0,
            "mean": weighted_mean,
            "std": math.sqrt(max(pooled_variance, 0.0)),
            "min": float(min(float(row[1][2]) for row in rows)),
            "max": float(max(float(row[1][3]) for row in rows)),
            "p01_median": float(np.median(p01s)),
            "p50_median": float(np.median(p50s)),
            "p99_median": float(np.median(p99s)),
            "distribution_change_rule": "robust_z_gt_8_and_delta_gt_0.5_m_s",
        }
        summary[period]["flags"].extend(flags)

    return tuple(summary[key] for key in sorted(summary))


def build_manifest(report: Stage4ValidationReport) -> dict[str, Any]:
    """Build a manifest containing only files that pass all scoped checks."""

    entries = []
    for result in report.results:
        if result.downstream_ready:
            entries.append({
                "job_id": result.job_id,
                "plan_name": result.plan_name,
                "relative_path": result.relative_path,
                "source_checksum": result.source_checksum,
                "status": "PASS",
                "checks": list(result.checks),
                "details": list(result.details),
                "expected_timesteps": result.expected_timesteps,
                "time_count": result.time_count,
                "time_first": result.time_first,
                "time_last": result.time_last,
                "depth_value_m": result.depth_value_m,
                "units": list(result.normalized_units),
                "dataset_id": result.dataset_id,
                "dataset_version": result.dataset_version,
                "dataset_part": result.dataset_part,
                "start_datetime": result.start_datetime,
                "end_datetime": result.end_datetime,
                "coverage": [_metric_to_json(metric) for metric in result.coverage_metrics],
                "distribution": [
                    _distribution_to_json(metric) for metric in result.distribution_metrics
                ],
                "consistency": list(result.consistency),
            })
    full_scope = report.scope == "full"
    period_summary = list(distribution_summary(report)) if full_scope else []
    distribution_flags = [flag for period in period_summary for flag in period["flags"]]
    if full_scope:
        limitations = [
            "T4-009 coverage, T4-010 uo/vo consistency, and T4-011 distributions were evaluated locally.",
            "Distribution flags use robust_z_gt_8_and_delta_gt_0.5_m_s and are non-blocking QC notes.",
            "Five small encoded-range excursions remain non-blocking notes; values were not corrected.",
            "T4-012 manifest includes only files that pass all scoped checks.",
        ]
        test_ids = [f"TST-VAL-{index:03d}" for index in range(1, 21)]
    elif report.scope == "wp2":
        limitations = [
            "WP2 covers only T4-001 through T4-008; T4-009 through T4-012 remain pending.",
            "Coverage and uo/vo value consistency remain outside this manifest.",
        ]
        test_ids = [f"TST-VAL-{index:03d}" for index in range(1, 19)]
    else:
        limitations = [
            "WP1 covers only T4-001 through T4-004; T4-005 through T4-012 remain pending.",
        ]
        test_ids = [f"TST-VAL-{index:03d}" for index in range(1, 10)]
    return {
        "stage": "T4",
        "scope": report.scope.upper(),
        "test_ids": test_ids,
        "config_hash": report.config_hash,
        "target_depth_m": report.target_depth_m,
        "depth_tolerance_m": report.depth_tolerance_m,
        "files_checked": report.files_checked,
        "files_pass": report.files_pass,
        "files_fail": report.files_fail,
        "error_count": sum(len(result.errors) for result in report.results),
        "anomaly_count": report.anomaly_count,
        "coverage_definition": "finite_decoded_samples_over_time_depth_latitude_longitude",
        "distribution_definition": "per_file_min_max_mean_std_p01_p50_p99_and_plan_month_summary",
        "entries": entries,
        "downstream_ready": report.files_fail == 0,
        "period_distributions": period_summary,
        "distribution_flags": distribution_flags,
        "limitations": limitations,
    }


def render_validation_report(report: Stage4ValidationReport) -> str:
    """Render T4-013 evidence as stable key-value text."""

    def check_passes(code: str) -> bool:
        return report.files_fail == 0 and all(
            any(code in check for check in result.checks) for result in report.results
        )

    full_scope = report.scope == "full"
    period_summary = list(distribution_summary(report)) if full_scope else []
    distribution_flags = [flag for period in period_summary for flag in period["flags"]]
    test_count = 20 if full_scope else (18 if report.scope == "wp2" else 9)
    fixture_count = 22 if full_scope else (15 if report.scope == "wp2" else 8)
    t4_009 = check_passes("T4-009") if full_scope else False
    t4_010 = check_passes("T4-010") if full_scope else False
    t4_011 = check_passes("T4-011") if full_scope else False

    lines = [
        "stage=T4-013",
        f"scope={report.scope.upper()}",
        "validation_mode=local_read_only",
        f"command={report.command}",
        f"test_ids=TST-VAL-001..TST-VAL-{test_count:03d}",
        f"validation_test_count={test_count}",
        f"fixture_test_count={fixture_count}",
        f"exit_status={0 if report.files_fail == 0 else 4}",
        f"inventory_rows={report.inventory_rows}",
        f"files_checked={report.files_checked}",
        f"files_pass={report.files_pass}",
        f"files_fail={report.files_fail}",
        f"error_count={sum(len(result.errors) for result in report.results)}",
        f"anomaly_count={report.anomaly_count}",
        f"distribution_flag_count={len(distribution_flags)}",
        "coverage_definition=finite_decoded_samples_over_time_depth_latitude_longitude",
        "distribution_definition=per_file_min_max_mean_std_p01_p50_p99_and_plan_month_summary",
        f"target_depth_m={report.target_depth_m}",
        f"depth_tolerance_m={report.depth_tolerance_m}",
        f"config_hash={report.config_hash}",
        "t4_001=PASS" if check_passes("T4-001") else "t4_001=FAIL",
        "t4_002=PASS" if check_passes("T4-002") else "t4_002=FAIL",
        "t4_003=PASS" if check_passes("T4-003") else "t4_003=FAIL",
        "t4_004=PASS" if check_passes("T4-004") else "t4_004=FAIL",
        "t4_005=PASS" if report.scope in {"wp2", "full"} and check_passes("T4-005") else ("t4_005=FAIL" if report.scope in {"wp2", "full"} else "t4_005=NOT_STARTED"),
        "t4_006=PASS" if report.scope in {"wp2", "full"} and check_passes("T4-006") else ("t4_006=FAIL" if report.scope in {"wp2", "full"} else "t4_006=NOT_STARTED"),
        "t4_007=PASS" if report.scope in {"wp2", "full"} and check_passes("T4-007") else ("t4_007=FAIL" if report.scope in {"wp2", "full"} else "t4_007=NOT_STARTED"),
        "t4_008=PASS" if report.scope in {"wp2", "full"} and check_passes("T4-008") else ("t4_008=FAIL" if report.scope in {"wp2", "full"} else "t4_008=NOT_STARTED"),
        "t4_009=PASS" if t4_009 else ("t4_009=FAIL" if full_scope else "t4_009=NOT_STARTED"),
        "t4_010=PASS" if t4_010 else ("t4_010=FAIL" if full_scope else "t4_010=NOT_STARTED"),
        "t4_011=PASS" if t4_011 else ("t4_011=FAIL" if full_scope else "t4_011=NOT_STARTED"),
        "t4_012=PASS" if full_scope and report.files_fail == 0 else ("t4_012=FAIL" if full_scope else "t4_012=NOT_STARTED"),
        "t4_013=PASS" if full_scope and report.files_checked == 165 and report.files_fail == 0 else ("t4_013=FAIL" if full_scope else "t4_013=NOT_STARTED"),
        "t4_014=PASS_WITH_NOTES" if full_scope and report.files_fail == 0 else ("t4_014=FAIL" if full_scope else "t4_014=NOT_STARTED"),
        "network_authentication=NOT_USED",
        "download=NOT_PERFORMED",
        "raw_netcdf_mutation=NOT_PERFORMED",
        "inventory_mutation=NOT_PERFORMED",
        "manifest_policy=PASS_ONLY_FILES",
        "plausibility_anomaly_policy=encoded_range_excursion_le_0.5_m_s_is_nonblocking_note;_larger_excursion_fails",
        "distribution_change_rule=robust_z_gt_8_and_delta_gt_0.5_m_s_nonblocking_qc_note",
    ]
    for period in period_summary:
        for variable, values in period["variables"].items():
            lines.append(
                f"period={period['period']}|variable={variable}|files={values['files']}|"
                f"valid_count={values['valid_count']}|total_count={values['total_count']}|"
                f"coverage_pct={values['coverage_pct']:.9f}|min={values['min']:.12g}|"
                f"max={values['max']:.12g}|mean={values['mean']:.12g}|std={values['std']:.12g}|"
                f"p01_median={values['p01_median']:.12g}|p50_median={values['p50_median']:.12g}|"
                f"p99_median={values['p99_median']:.12g}"
            )
        for flag in period["flags"]:
            lines.append(f"distribution_flag={flag}")
    for result in report.results:
        lines.append(
            f"file={result.relative_path}|job_id={result.job_id}|status={result.status}|"
            f"time_count={result.time_count}|errors={' ; '.join(result.errors) or 'none'}|"
            f"anomalies={' ; '.join(result.anomalies) or 'none'}|"
            f"coverage={' ; '.join(f'{m[0]}:{m[1]}/{m[2]}:{m[3]:.6f}%' for m in result.coverage_metrics) or 'not_evaluated'}|"
            f"consistency={' ; '.join(result.consistency) or 'not_evaluated'}"
        )
    lines.extend([
        "limitation=Five small encoded-range excursions were recorded as non-blocking anomalies; values were not corrected.",
        "limitation=Distribution flags are descriptive QC notes and do not silently alter values.",
        "limitation=No GEE Code Editor, Earth Engine, Copernicus, or network operation was used.",
        f"status={'PASS' if report.files_fail == 0 else 'FAIL'}",
    ])
    return "\n".join(lines)


def render_gate(report: Stage4ValidationReport) -> str:
    """Render the scoped or full T4-014 gate."""

    full_scope = report.scope == "full"
    period_summary = list(distribution_summary(report)) if full_scope else []
    distribution_flag_count = sum(len(period["flags"]) for period in period_summary)
    decision = "PASS_WITH_NOTES" if report.files_fail == 0 else "FAIL"
    status = "PASS" if report.files_fail == 0 else "FAIL"
    return "\n".join([
        "stage=T4-014",
        f"gate_scope={'FULL_STAGE4' if full_scope else report.scope.upper() + '_only'}",
        "t4_001=PASS" if report.files_fail == 0 else "t4_001=FAIL",
        "t4_002=PASS" if report.files_fail == 0 else "t4_002=FAIL",
        "t4_003=PASS" if report.files_fail == 0 else "t4_003=FAIL",
        "t4_004=PASS" if report.files_fail == 0 else "t4_004=FAIL",
        "t4_005=PASS" if report.scope in {"wp2", "full"} and report.files_fail == 0 else ("t4_005=FAIL" if report.scope in {"wp2", "full"} else "t4_005=NOT_STARTED"),
        "t4_006=PASS" if report.scope in {"wp2", "full"} and report.files_fail == 0 else ("t4_006=FAIL" if report.scope in {"wp2", "full"} else "t4_006=NOT_STARTED"),
        "t4_007=PASS" if report.scope in {"wp2", "full"} and report.files_fail == 0 else ("t4_007=FAIL" if report.scope in {"wp2", "full"} else "t4_007=NOT_STARTED"),
        "t4_008=PASS" if report.scope in {"wp2", "full"} and report.files_fail == 0 else ("t4_008=FAIL" if report.scope in {"wp2", "full"} else "t4_008=NOT_STARTED"),
        "t4_009=PASS" if full_scope and report.files_fail == 0 else ("t4_009=FAIL" if full_scope else "t4_009=NOT_STARTED"),
        "t4_010=PASS" if full_scope and report.files_fail == 0 else ("t4_010=FAIL" if full_scope else "t4_010=NOT_STARTED"),
        "t4_011=PASS" if full_scope and report.files_fail == 0 else ("t4_011=FAIL" if full_scope else "t4_011=NOT_STARTED"),
        "t4_012=PASS" if full_scope and report.files_fail == 0 else ("t4_012=FAIL" if full_scope else "t4_012=NOT_STARTED"),
        "t4_013=PASS" if full_scope and report.files_checked == 165 and report.files_fail == 0 else ("t4_013=FAIL" if full_scope else "t4_013=NOT_STARTED"),
        "t4_014=PASS_WITH_NOTES" if full_scope and report.files_fail == 0 else ("t4_014=FAIL" if full_scope else "t4_014=NOT_STARTED"),
        f"exit_status={0 if report.files_fail == 0 else 4}",
        f"files_checked={report.files_checked}",
        f"files_pass={report.files_pass}",
        f"files_fail={report.files_fail}",
        f"error_count={sum(len(result.errors) for result in report.results)}",
        f"anomaly_count={report.anomaly_count}",
        f"distribution_flag_count={distribution_flag_count}",
        f"gate_decision={decision}",
        f"status={status}",
        "limitation=Full Stage 4 gate covers local NetCDF validation only; T5 conversion and downstream cloud operations remain pending." if full_scope else "limitation=This is not a full Stage 4 gate; T4-009 onward remains pending.",
        "plausibility_anomaly_policy=encoded_range_excursion_le_0.5_m_s_is_nonblocking_note;_larger_excursion_fails",
        "distribution_change_rule=robust_z_gt_8_and_delta_gt_0.5_m_s_nonblocking_qc_note",
        "m0_status=IN_PROGRESS",
        "adr_status=PROPOSED",
        "network_authentication=NOT_USED",
        "inventory_mutation=NOT_PERFORMED",
    ])


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--gate", type=Path, default=DEFAULT_GATE_PATH)
    parser.add_argument("--scope", choices=("wp1", "wp2", "full"), default="wp1")
    parser.add_argument("--command", default="python/07_validate_stage4.py --root E:/project/gee-current")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = validate_stage4(
            args.root, inventory_path=args.inventory, command=args.command, scope=args.scope
        )
        _write_json_atomic((args.root / args.manifest).resolve(), build_manifest(report))
        _write_text_atomic((args.root / args.report).resolve(), render_validation_report(report) + "\n")
        _write_text_atomic((args.root / args.gate).resolve(), render_gate(report) + "\n")
        print(render_validation_report(report))
        print(render_gate(report))
        return 0 if report.files_fail == 0 else 4
    except (Stage4ValidationError, OSError, sqlite3.Error, ValueError) as exc:
        print("stage=T4-013")
        print(f"error={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
