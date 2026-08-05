"""Offline NetCDF-to-GeoTIFF conversion for the Stage 5 pilot.

The converter accepts only entries from the validated Stage 4 manifest.  It
decodes CF packing once with xarray, reorders monotonic coordinates when
needed for a north-up raster, and never resamples the source grid.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import Affine, from_origin
import xarray as xr

from python.checksum import sha256_file, verify_sha256
from python.common.constants import (
    ANALYSIS_DEPTH_M,
    CURRENT_UNITS,
    CURRENT_VARIABLES,
    DEPTH_TOLERANCE_M,
    PRODUCT_ID,
)


PIPELINE_VERSION = "stage5-conversion-pilot-1.0"
CRS = "EPSG:4326"
NODATA_VALUE = -9999.0
# Native GLORYS coordinates are stored as float32 and therefore have small
# alternating rounding jitter around the regular 1/12-degree grid.  This is a
# coordinate-representation tolerance only; no values are interpolated or
# resampled.
GRID_TOLERANCE = 2e-5


class ConversionError(ValueError):
    """Raised when a conversion contract is not satisfied."""


@dataclass(frozen=True)
class PreparedSource:
    """CF-decoded source arrays and the native north-up grid description."""

    uo: np.ndarray
    vo: np.ndarray
    times: tuple[pd.Timestamp, ...]
    latitude: np.ndarray
    longitude: np.ndarray
    transform: Affine
    depth_m: float


def _utc_now() -> str:
    """Return a UTC timestamp suitable for provenance metadata."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _require_text(entry: Mapping[str, Any], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value:
        raise ConversionError(f"manifest field {key!r} must be a non-empty string")
    return value


def _resolve_under_root(root: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ConversionError("manifest relative_path must not be absolute")
    root_resolved = root.resolve()
    resolved = (root_resolved / candidate).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ConversionError("manifest relative_path escapes repository root") from exc
    return resolved


def load_manifest_entry(manifest_path: str | Path, job_id: str) -> dict[str, Any]:
    """Load and validate one PASS entry from a Stage 4 manifest."""

    path = Path(manifest_path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConversionError(f"cannot read manifest: {path}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("entries"), list):
        raise ConversionError("manifest must contain an entries list")
    matches = [entry for entry in document["entries"] if isinstance(entry, dict) and entry.get("job_id") == job_id]
    if len(matches) != 1:
        raise ConversionError(f"manifest must contain exactly one entry for job_id={job_id!r}")
    entry = matches[0]
    if entry.get("status") != "PASS":
        raise ConversionError(f"manifest entry {job_id!r} is not PASS")
    for key in ("relative_path", "source_checksum", "dataset_id", "dataset_version", "dataset_part"):
        _require_text(entry, key)
    return entry


def config_hash(paths: Iterable[str | Path], *, root: str | Path | None = None) -> str:
    """Hash the ordered contents and relative names of explicit config files."""

    raw_paths = tuple(sorted((Path(path) for path in paths), key=lambda path: path.as_posix()))
    if not raw_paths:
        raise ConversionError("at least one config file is required for config_hash")
    root_path = Path(root).resolve() if root is not None else None
    digest = hashlib.sha256()
    for raw_path in raw_paths:
        path = raw_path.resolve()
        if not path.is_file():
            raise ConversionError(f"config file does not exist: {path}")
        if root_path is not None:
            try:
                label = path.relative_to(root_path).as_posix()
            except ValueError as exc:
                raise ConversionError(f"config file is outside root: {path}") from exc
        else:
            label = raw_path.as_posix()
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _monotonic_direction(values: np.ndarray, name: str) -> int:
    if values.ndim != 1 or values.size < 2:
        raise ConversionError(f"{name} must be a one-dimensional coordinate with at least two cells")
    differences = np.diff(values.astype(np.float64))
    if np.all(differences > 0):
        return 1
    if np.all(differences < 0):
        return -1
    raise ConversionError(f"{name} must be strictly monotonic")


def _grid_step(values: np.ndarray, name: str) -> float:
    steps = np.abs(np.diff(values.astype(np.float64)))
    representative_step = float(np.median(steps))
    if not np.allclose(steps, representative_step, rtol=0.0, atol=GRID_TOLERANCE):
        raise ConversionError(f"{name} is irregular; conversion would require resampling")
    if not np.isfinite(representative_step) or representative_step <= 0:
        raise ConversionError(f"{name} has an invalid grid step")
    return representative_step


def _validate_manifest_against_dataset(entry: Mapping[str, Any], source: xr.Dataset) -> float:
    missing_variables = [name for name in CURRENT_VARIABLES if name not in source.data_vars]
    if missing_variables:
        raise ConversionError(f"missing required variables: {','.join(missing_variables)}")
    required_dims = {"time", "depth", "latitude", "longitude"}
    missing_dims = required_dims.difference(source.dims)
    if missing_dims:
        raise ConversionError(f"missing required dimensions: {','.join(sorted(missing_dims))}")
    for name in CURRENT_VARIABLES:
        if source[name].attrs.get("units") != CURRENT_UNITS:
            raise ConversionError(f"{name} units must be exactly {CURRENT_UNITS!r}; no silent conversion")
        if set(source[name].dims) != required_dims:
            raise ConversionError(f"{name} dimensions do not contain exactly the required dimensions")
    if source.sizes["depth"] != 1:
        raise ConversionError(f"expected one selected depth, found {source.sizes['depth']}")
    depth_m = float(source["depth"].values[0])
    if abs(depth_m - ANALYSIS_DEPTH_M) > DEPTH_TOLERANCE_M:
        raise ConversionError(f"depth {depth_m} is outside the configured tolerance")
    expected_count = entry.get("expected_timesteps")
    actual_times = pd.DatetimeIndex(source["time"].values)
    if not isinstance(expected_count, int) or expected_count <= 0 or len(actual_times) != expected_count:
        raise ConversionError("timestamp count does not match the validated manifest")
    if not actual_times.is_unique or not actual_times.is_monotonic_increasing:
        raise ConversionError("timestamps must be unique and strictly increasing")
    start = pd.Timestamp(_require_text(entry, "start_datetime"))
    end = pd.Timestamp(_require_text(entry, "end_datetime"))
    if actual_times[0] != start or actual_times[-1] > end:
        raise ConversionError("timestamps fall outside the validated manifest interval")
    for coordinate in ("latitude", "longitude"):
        _monotonic_direction(np.asarray(source[coordinate].values), coordinate)
        _grid_step(np.asarray(source[coordinate].values), coordinate)
    uo = np.asarray(source["uo"].transpose("time", "depth", "latitude", "longitude").isel(depth=0).values)
    vo = np.asarray(source["vo"].transpose("time", "depth", "latitude", "longitude").isel(depth=0).values)
    if not np.array_equal(np.isfinite(uo), np.isfinite(vo)):
        raise ConversionError("uo and vo masks differ; refusing to collapse independent masks")
    return depth_m


def _prepare_source(entry: Mapping[str, Any], source: xr.Dataset) -> PreparedSource:
    """Validate and orient one decoded source dataset without resampling."""

    depth_m = _validate_manifest_against_dataset(entry, source)
    latitude = np.asarray(source["latitude"].values, dtype=np.float64)
    longitude = np.asarray(source["longitude"].values, dtype=np.float64)
    uo = np.asarray(source["uo"].transpose("time", "depth", "latitude", "longitude").isel(depth=0).values)
    vo = np.asarray(source["vo"].transpose("time", "depth", "latitude", "longitude").isel(depth=0).values)
    if _monotonic_direction(latitude, "latitude") > 0:
        latitude = latitude[::-1]
        uo = uo[:, ::-1, :]
        vo = vo[:, ::-1, :]
    if _monotonic_direction(longitude, "longitude") < 0:
        longitude = longitude[::-1]
        uo = uo[:, :, ::-1]
        vo = vo[:, :, ::-1]
    dx = _grid_step(longitude, "longitude")
    dy = _grid_step(latitude, "latitude")
    transform = from_origin(
        float(longitude[0] - dx / 2),
        float(latitude[0] + dy / 2),
        dx,
        dy,
    )
    return PreparedSource(
        uo=uo,
        vo=vo,
        times=tuple(pd.Timestamp(value) for value in pd.DatetimeIndex(source["time"].values)),
        latitude=latitude,
        longitude=longitude,
        transform=transform,
        depth_m=depth_m,
    )


def _atomic_write_raster(path: Path, arrays: np.ndarray, transform: Affine, tags: Mapping[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ConversionError(f"output exists; refusing overwrite: {path}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
        with rasterio.open(
            temporary,
            "w",
            driver="GTiff",
            height=arrays.shape[1],
            width=arrays.shape[2],
            count=2,
            dtype="float32",
            crs=CRS,
            transform=transform,
            nodata=NODATA_VALUE,
            compress="deflate",
            predictor=3,
        ) as destination:
            destination.write(arrays)
            destination.set_band_description(1, "uo")
            destination.set_band_description(2, "vo")
            destination.update_tags(**dict(tags))
        os.replace(temporary, path)
    except (OSError, rasterio.errors.RasterioError) as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise ConversionError(f"atomic GeoTIFF write failed: {path}") from exc


def convert_job(
    *,
    root: str | Path,
    entry: Mapping[str, Any],
    output_dir: str | Path,
    config_hash_value: str,
    prefix: str,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Convert one validated manifest job into native-grid two-band GeoTIFFs."""

    root_path = Path(root).resolve()
    source_path = _resolve_under_root(root_path, _require_text(entry, "relative_path"))
    expected_checksum = _require_text(entry, "source_checksum")
    if not verify_sha256(source_path, expected_checksum):
        raise ConversionError("source checksum does not match validated manifest")
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)
    if not config_hash_value or len(config_hash_value) != 64:
        raise ConversionError("config_hash must be a 64-character SHA-256 digest")
    if not prefix:
        raise ConversionError("prefix must be non-empty")
    outputs: list[dict[str, Any]] = []
    with xr.open_dataset(source_path, engine="h5netcdf", decode_cf=True, mask_and_scale=True) as source:
        prepared = _prepare_source(entry, source)
        for index, timestamp in enumerate(prepared.times):
            output_file = output_path / f"{prefix}_{timestamp.strftime('%Y%m%dT%H%M%S')}.tif"
            if output_file.exists() and not overwrite:
                raise ConversionError(f"output exists; pass overwrite=True to replace: {output_file}")
            if output_file.exists() and overwrite:
                output_file.unlink()
            uo = np.asarray(prepared.uo[index], dtype=np.float64)
            vo = np.asarray(prepared.vo[index], dtype=np.float64)
            valid = np.isfinite(uo) & np.isfinite(vo)
            arrays = np.stack(
                [np.where(valid, uo, NODATA_VALUE), np.where(valid, vo, NODATA_VALUE)], axis=0
            ).astype(np.float32)
            if np.any(arrays[:, valid] == np.float32(NODATA_VALUE)):
                raise ConversionError("valid source value collides with configured NoData")
            tags = {
                "product_id": PRODUCT_ID,
                "dataset_id": _require_text(entry, "dataset_id"),
                "dataset_version": _require_text(entry, "dataset_version"),
                "dataset_part": _require_text(entry, "dataset_part"),
                "source_file": source_path.name,
                "source_checksum": expected_checksum,
                "job_id": _require_text(entry, "job_id"),
                "plan_name": _require_text(entry, "plan_name"),
                "time": timestamp.isoformat(),
                "depth_m": repr(prepared.depth_m),
                "variables": "uo,vo",
                "units": CURRENT_UNITS,
                "crs": CRS,
                "config_hash": config_hash_value,
                "pipeline_version": PIPELINE_VERSION,
                "resampling": "none",
                "nodata": repr(NODATA_VALUE),
                "created_utc": _utc_now(),
            }
            _atomic_write_raster(output_file, arrays, prepared.transform, tags)
            outputs.append(
                {
                    "path": str(output_file),
                    "time": timestamp.isoformat(),
                    "sha256": sha256_file(output_file),
                    "valid_pixel_count": int(valid.sum()),
                    "total_pixel_count": int(valid.size),
                }
            )
    return {
        "status": "PASS_WITH_NOTES",
        "job_id": _require_text(entry, "job_id"),
        "source": str(source_path),
        "source_checksum": expected_checksum,
        "output_count": len(outputs),
        "outputs": outputs,
        "bands": list(CURRENT_VARIABLES),
        "dtype": "float32",
        "crs": CRS,
        "nodata": NODATA_VALUE,
        "resampling": "none",
        "config_hash": config_hash_value,
        "pipeline_version": PIPELINE_VERSION,
        "limitations": [
            "Pilot conversion is local/offline only.",
            "No Earth Engine upload or cloud computation was performed.",
            "T5-008 collection conversion remains outside this work package.",
        ],
    }


def _required_tag(tags: Mapping[str, str], key: str, expected: str) -> None:
    actual = tags.get(key)
    if actual != expected:
        raise ConversionError(f"GeoTIFF metadata {key!r} mismatch: {actual!r} != {expected!r}")


def compare_job_outputs(
    *,
    root: str | Path,
    entry: Mapping[str, Any],
    geotiff_dir: str | Path,
    prefix: str,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Compare every GeoTIFF in one job against its decoded source values."""

    if not np.isfinite(tolerance) or tolerance <= 0:
        raise ConversionError("tolerance must be a finite positive number")
    root_path = Path(root).resolve()
    source_path = _resolve_under_root(root_path, _require_text(entry, "relative_path"))
    expected_checksum = _require_text(entry, "source_checksum")
    if not verify_sha256(source_path, expected_checksum):
        raise ConversionError("source checksum does not match validated manifest")
    raster_dir = Path(geotiff_dir).resolve()
    if not raster_dir.is_dir():
        raise ConversionError(f"GeoTIFF directory does not exist: {raster_dir}")
    with xr.open_dataset(source_path, engine="h5netcdf", decode_cf=True, mask_and_scale=True) as source:
        prepared = _prepare_source(entry, source)
        expected_paths = [raster_dir / f"{prefix}_{timestamp.strftime('%Y%m%dT%H%M%S')}.tif" for timestamp in prepared.times]
        matching_paths = sorted(raster_dir.glob(f"{prefix}_*.tif"))
        if len(matching_paths) != len(expected_paths):
            raise ConversionError(
                f"GeoTIFF count mismatch: found {len(matching_paths)}, expected {len(expected_paths)}"
            )
        file_reports: list[dict[str, Any]] = []
        all_differences: list[float] = []
        max_difference = 0.0
        max_location: dict[str, Any] | None = None
        for index, (timestamp, path) in enumerate(zip(prepared.times, expected_paths, strict=True)):
            if not path.is_file():
                raise ConversionError(f"missing GeoTIFF: {path}")
            with rasterio.open(path) as raster:
                if raster.count != 2 or raster.dtypes != ("float32", "float32"):
                    raise ConversionError(f"{path.name}: expected two float32 bands")
                if raster.crs is None or raster.crs.to_epsg() != 4326:
                    raise ConversionError(f"{path.name}: CRS is not EPSG:4326")
                if raster.transform != prepared.transform:
                    raise ConversionError(f"{path.name}: affine transform mismatch")
                if tuple(raster.descriptions) != CURRENT_VARIABLES:
                    raise ConversionError(f"{path.name}: band descriptions are not uo,vo")
                if raster.nodata != NODATA_VALUE:
                    raise ConversionError(f"{path.name}: NoData value mismatch")
                tags = raster.tags()
                _required_tag(tags, "product_id", PRODUCT_ID)
                _required_tag(tags, "source_file", source_path.name)
                _required_tag(tags, "source_checksum", expected_checksum)
                _required_tag(tags, "job_id", _require_text(entry, "job_id"))
                _required_tag(tags, "plan_name", _require_text(entry, "plan_name"))
                _required_tag(tags, "dataset_id", _require_text(entry, "dataset_id"))
                _required_tag(tags, "dataset_version", _require_text(entry, "dataset_version"))
                _required_tag(tags, "dataset_part", _require_text(entry, "dataset_part"))
                _required_tag(tags, "time", timestamp.isoformat())
                _required_tag(tags, "crs", CRS)
                _required_tag(tags, "variables", "uo,vo")
                _required_tag(tags, "units", CURRENT_UNITS)
                _required_tag(tags, "resampling", "none")
                _required_tag(tags, "pipeline_version", PIPELINE_VERSION)
                if len(tags.get("config_hash", "")) != 64:
                    raise ConversionError(f"{path.name}: config_hash metadata is missing or invalid")
                try:
                    depth_tag = float(tags["depth_m"])
                except (KeyError, ValueError) as exc:
                    raise ConversionError(f"{path.name}: depth_m metadata is invalid") from exc
                if abs(depth_tag - ANALYSIS_DEPTH_M) > DEPTH_TOLERANCE_M:
                    raise ConversionError(f"{path.name}: depth_m metadata is outside tolerance")
                expected = np.stack([prepared.uo[index], prepared.vo[index]], axis=0)
                actual_masked = raster.read(masked=True)
                actual = actual_masked.filled(np.nan).astype(np.float64)
                expected_mask = ~np.isfinite(expected)
                actual_mask = np.ma.getmaskarray(actual_masked)
                if actual.shape != expected.shape or not np.array_equal(actual_mask, expected_mask):
                    raise ConversionError(f"{path.name}: shape or mask mismatch")
                valid = np.isfinite(expected)
                differences = np.abs(actual[valid] - expected[valid])
                if differences.size and float(differences.max()) > tolerance:
                    raise ConversionError(
                        f"{path.name}: max absolute difference {float(differences.max())} exceeds {tolerance}"
                    )
                if differences.size:
                    all_differences.extend(float(value) for value in differences)
                    file_max_index = int(np.argmax(np.abs(actual[valid] - expected[valid])))
                    valid_indices = np.argwhere(valid)
                    location = valid_indices[file_max_index]
                    file_max = float(differences.max())
                    if file_max >= max_difference:
                        max_difference = file_max
                        max_location = {
                            "time": timestamp.isoformat(),
                            "band_index": int(location[0]) + 1,
                            "row": int(location[1]),
                            "column": int(location[2]),
                        }
                file_reports.append(
                    {
                        "path": str(path),
                        "time": timestamp.isoformat(),
                        "valid_pixel_count": int(valid[0].sum()),
                        "max_absolute_error": float(differences.max()) if differences.size else 0.0,
                        "mean_absolute_error": float(differences.mean()) if differences.size else 0.0,
                        "p95_absolute_error": float(np.percentile(differences, 95)) if differences.size else 0.0,
                        "p99_absolute_error": float(np.percentile(differences, 99)) if differences.size else 0.0,
                    }
                )
    return {
        "status": "PASS_WITH_NOTES",
        "job_id": _require_text(entry, "job_id"),
        "source": str(source_path),
        "source_checksum": expected_checksum,
        "file_count": len(file_reports),
        "band_count": 2,
        "bands": list(CURRENT_VARIABLES),
        "dtype": "float32",
        "crs": CRS,
        "nodata": NODATA_VALUE,
        "resampling": "none",
        "absolute_tolerance": tolerance,
        "max_absolute_difference": max_difference,
        "mean_absolute_difference": float(np.mean(all_differences)) if all_differences else 0.0,
        "p95_absolute_difference": float(np.percentile(all_differences, 95)) if all_differences else 0.0,
        "p99_absolute_difference": float(np.percentile(all_differences, 99)) if all_differences else 0.0,
        "max_error_location": max_location,
        "files": file_reports,
        "limitations": [
            "Comparison is local/offline and does not validate Earth Engine ingestion.",
            "No resampling or reprojection was performed by this comparator.",
        ],
    }


__all__ = [
    "CRS",
    "ConversionError",
    "GRID_TOLERANCE",
    "NODATA_VALUE",
    "PIPELINE_VERSION",
    "PreparedSource",
    "config_hash",
    "compare_job_outputs",
    "convert_job",
    "load_manifest_entry",
]
