"""Build and validate the offline T6-004 sample image manifests.

This module only reads local Stage 5 evidence and raster headers.  It never
authenticates, accesses a network, uploads an asset, or starts an Earth Engine
task.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping


SOURCE_JOB_ID = "daily_jfm_2015_01"
SAMPLE_TIME = "2015-01-01T00:00:00"
SAMPLE_PRODUCT_TYPE = "speed"
SOURCE_MANIFEST = Path("outputs/manifests/stage_5_conversion_manifest.json")
VALIDATED_MANIFEST = Path("outputs/manifests/stage_4_validated_manifest.json")
ANALYTICS_MANIFEST = Path("outputs/manifests/stage_5_analytics_manifest.json")
ASSET_NAMING = Path("config/asset_naming.json")


class ManifestError(ValueError):
    """Raised when a sample manifest cannot be built safely."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read JSON manifest: {path}") from exc
    if not isinstance(value, dict):
        raise ManifestError(f"JSON manifest must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ManifestError(f"cannot hash local file: {path}") from exc
    return digest.hexdigest()


def _repo_path(root: Path, raw_path: str) -> Path:
    """Resolve a Windows or POSIX evidence path without accepting path escape."""

    normalized = str(raw_path).replace("\\", "/")
    marker = "/gee-current/"
    if marker in normalized:
        relative = normalized.split(marker, 1)[1]
    elif normalized.startswith("gee-current/"):
        relative = normalized.removeprefix("gee-current/")
    else:
        relative = normalized
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ManifestError(f"evidence path escapes repository root: {raw_path}") from exc
    return candidate


def _relative_path(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ManifestError(f"path is outside repository root: {path}") from exc


def _windows_basename(raw_path: str) -> str:
    return str(raw_path).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]


def _require_text(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestError(f"manifest field {key!r} must be non-empty text")
    return value


def _iso_z(value: str) -> str:
    """Normalize a Stage 5 naive UTC timestamp to an explicit UTC timestamp."""

    candidate = value[:-1] if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ManifestError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.isoformat(timespec="seconds") + "Z"


def _period(value: str) -> tuple[str, str, str, str]:
    start = datetime.fromisoformat(value)
    end = start + timedelta(days=1)
    return (
        start.date().isoformat(),
        end.date().isoformat(),
        start.isoformat(timespec="seconds") + "Z",
        end.isoformat(timespec="seconds") + "Z",
    )


def _validate_bucket(bucket: str) -> str:
    if not isinstance(bucket, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]", bucket):
        raise ManifestError("gcs_bucket must be an explicit DNS-compatible bucket name")
    return bucket


def _validate_created_utc(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ManifestError("created_utc must be an explicit UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManifestError("created_utc is not a valid timestamp") from exc
    return value


_TIFF_TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 12: 8}


def _tiff_values(handle: Any, endian: str, field_type: int, count: int, raw: bytes) -> tuple[Any, ...]:
    size = _TIFF_TYPE_SIZES.get(field_type)
    if size is None:
        raise ManifestError(f"unsupported GeoTIFF field type: {field_type}")
    payload_size = size * count
    if payload_size <= 4:
        payload = raw[:payload_size]
    else:
        payload_offset = struct.unpack(endian + "I", raw)[0]
        current_position = handle.tell()
        handle.seek(payload_offset)
        payload = handle.read(payload_size)
        handle.seek(current_position)
        if len(payload) != payload_size:
            raise ManifestError("truncated GeoTIFF tag payload")
    if len(payload) != payload_size:
        raise ManifestError("truncated GeoTIFF inline tag payload")
    formats = {1: "B", 2: "c", 3: "H", 4: "I", 5: "II", 12: "d"}
    fmt = formats[field_type]
    if field_type == 5:
        return tuple(tuple(value) for value in struct.iter_unpack(endian + fmt, payload))
    return tuple(struct.unpack(endian + fmt * count, payload))


def read_geotiff_grid(path: Path) -> dict[str, Any]:
    """Read the minimal north-up GeoTIFF grid tags needed by the manifest."""

    tags: dict[int, tuple[Any, ...]] = {}
    try:
        with path.open("rb") as handle:
            byte_order = handle.read(2)
            if byte_order == b"II":
                endian = "<"
            elif byte_order == b"MM":
                endian = ">"
            else:
                raise ManifestError(f"unsupported TIFF byte order: {path}")
            if struct.unpack(endian + "H", handle.read(2))[0] != 42:
                raise ManifestError(f"unsupported TIFF header: {path}")
            ifd_offset = struct.unpack(endian + "I", handle.read(4))[0]
            handle.seek(ifd_offset)
            entry_count = struct.unpack(endian + "H", handle.read(2))[0]
            for _ in range(entry_count):
                entry = handle.read(12)
                if len(entry) != 12:
                    raise ManifestError(f"truncated TIFF directory: {path}")
                tag, field_type, count = struct.unpack(endian + "HHI", entry[:8])
                if tag not in {256, 257, 33550, 33922}:
                    continue
                tags[tag] = _tiff_values(handle, endian, field_type, count, entry[8:12])
    except OSError as exc:
        raise ManifestError(f"cannot read GeoTIFF: {path}") from exc

    try:
        width = int(tags[256][0])
        height = int(tags[257][0])
        scale = tags[33550]
        tiepoint = tags[33922]
        pixel_width = float(scale[0])
        pixel_height = float(scale[1])
        origin_x = float(tiepoint[3])
        origin_y = float(tiepoint[4])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ManifestError(f"GeoTIFF lacks required north-up grid tags: {path}") from exc
    if width < 1 or height < 1 or pixel_width <= 0 or pixel_height <= 0:
        raise ManifestError(f"invalid GeoTIFF dimensions or scale: {path}")
    return {
        "crs": "EPSG:4326",
        "transform": [pixel_width, 0.0, origin_x, 0.0, -pixel_height, origin_y],
        "shape": [height, width],
    }


def _find_job(conversion: Mapping[str, Any]) -> dict[str, Any]:
    jobs = conversion.get("jobs")
    if not isinstance(jobs, list):
        raise ManifestError("conversion manifest jobs must be a list")
    matches = [job for job in jobs if isinstance(job, dict) and job.get("job_id") == SOURCE_JOB_ID]
    if len(matches) != 1:
        raise ManifestError(f"expected exactly one conversion job: {SOURCE_JOB_ID}")
    job = matches[0]
    if job.get("status") not in {"PASS", "PASS_WITH_NOTES"}:
        raise ManifestError("sample conversion job is not passing")
    return job


def _find_validated_entry(validated: Mapping[str, Any]) -> dict[str, Any]:
    entries = validated.get("entries")
    if not isinstance(entries, list):
        raise ManifestError("validated manifest entries must be a list")
    matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("job_id") == SOURCE_JOB_ID]
    if len(matches) != 1:
        raise ManifestError(f"expected exactly one validated entry: {SOURCE_JOB_ID}")
    entry = matches[0]
    if entry.get("status") != "PASS":
        raise ManifestError("sample validated entry is not PASS")
    return entry


def _find_output(job: Mapping[str, Any]) -> dict[str, Any]:
    outputs = job.get("outputs")
    if not isinstance(outputs, list):
        raise ManifestError("conversion job outputs must be a list")
    matches = [output for output in outputs if isinstance(output, dict) and output.get("time") == SAMPLE_TIME]
    if len(matches) != 1:
        raise ManifestError(f"expected exactly one source output at {SAMPLE_TIME}")
    return matches[0]


def _find_product(analytics: Mapping[str, Any]) -> dict[str, Any]:
    products = analytics.get("products")
    if not isinstance(products, list):
        raise ManifestError("analytics products must be a list")
    matches = [
        product
        for product in products
        if isinstance(product, dict)
        and product.get("product_type") == SAMPLE_PRODUCT_TYPE
        and product.get("plan_name") == "daily_jfm"
        and product.get("time") == SAMPLE_TIME
    ]
    if len(matches) != 1:
        raise ManifestError("expected exactly one speed product at the sample time")
    return matches[0]


def _find_mask(analytics: Mapping[str, Any]) -> str:
    masks = analytics.get("masks")
    matches = [
        mask
        for mask in masks or []
        if isinstance(mask, dict) and mask.get("analysis_plan_id") == "daily_jfm"
    ]
    if len(matches) != 1 or not isinstance(matches[0].get("mask_sha256"), str):
        raise ManifestError("daily_jfm static mask checksum is missing")
    return matches[0]["mask_sha256"]


def _common_band(nodata: int = -9999) -> dict[str, Any]:
    return {
        "pyramidingPolicy": "MEAN",
        "missingData": {"values": [nodata]},
    }


def _source_manifest(
    *,
    root: Path,
    naming: Mapping[str, Any],
    job: Mapping[str, Any],
    validated_entry: Mapping[str, Any],
    output: Mapping[str, Any],
    grid: Mapping[str, Any],
    gcs_bucket: str,
    created_utc: str,
    aoi_id: str,
) -> dict[str, Any]:
    period_start, period_end, start_time, end_time = _period(SAMPLE_TIME)
    output_path = _repo_path(root, _require_text(output, "path"))
    source_filename = _windows_basename(_require_text(job, "source"))
    stem = "glorys12v1_d_20150101_d0p494025m"
    asset_collection = _require_text(naming["paths"], "daily_jfm_collection")
    band_uo = {"id": "uo", "tilesetBandIndex": 0, **_common_band()}
    band_vo = {"id": "vo", "tilesetBandIndex": 1, **_common_band()}
    return {
        "schema_version": "gee-source-asset-1.0",
        "asset_role": "source",
        "name": f"{asset_collection}/{stem}",
        "tilesets": [
            {
                "id": "source",
                "sources": [{"uris": [f"gs://{gcs_bucket}/t6-004/source/{output_path.name}"]}],
            }
        ],
        "bands": [band_uo, band_vo],
        "properties": {
            "product_id": "GLOBAL_MULTIYEAR_PHY_001_030",
            "dataset_id": _require_text(validated_entry, "dataset_id"),
            "dataset_version": _require_text(validated_entry, "dataset_version"),
            "dataset_part": _require_text(validated_entry, "dataset_part"),
            "source_model": "GLORYS12V1",
            "processing_type": "reanalysis",
            "temporal_resolution": "daily_mean",
            "period_type": "daily_jfm",
            "period_start": period_start,
            "period_end": period_end,
            "period_end_inclusive": False,
            "depth_m": 0.494025,
            "depth_label": "top_model_layer",
            "uo_units": "m s-1",
            "vo_units": "m s-1",
            "direction_convention": "towards_clockwise_from_north",
            "source_crs": _require_text(job, "crs"),
            "source_grid": dict(grid),
            "conversion_version": _require_text(job, "pipeline_version"),
            "pipeline_version": _require_text(job, "pipeline_version"),
            "config_hash": _require_text(job, "config_hash"),
            "source_filename": source_filename,
            "source_checksum": _require_text(job, "source_checksum"),
            "nodata_value": -9999,
            "mask_policy": "joint_uo_vo_valid",
            "is_reanalysis": True,
            "tides_included": False,
            "data_status": "validated_with_notes",
            "aoi_id": aoi_id,
            "usage_limitations": "Selected sample only; native GLORYS12V1 model grid; no tides; not operational or engineering use.",
            "created_utc": created_utc,
        },
        "startTime": start_time,
        "endTime": end_time,
    }


def _derived_manifest(
    *,
    root: Path,
    naming: Mapping[str, Any],
    job: Mapping[str, Any],
    output: Mapping[str, Any],
    product: Mapping[str, Any],
    grid: Mapping[str, Any],
    mask_checksum: str,
    conversion_manifest_sha256: str,
    analytics: Mapping[str, Any],
    gcs_bucket: str,
    created_utc: str,
    aoi_id: str,
) -> dict[str, Any]:
    period_start, period_end, start_time, end_time = _period(SAMPLE_TIME)
    derived_path = _repo_path(root, _require_text(product, "path"))
    source_path = _repo_path(root, _require_text(output, "path"))
    source_checksum = _require_text(output, "sha256")
    reference_years = analytics.get("analysis_period", {}).get("years")
    if not isinstance(reference_years, list) or len(reference_years) < 2:
        raise ManifestError("analytics analysis period years are missing")
    derived_collection = _require_text(naming["paths"], "derived")
    stem = "glorys12v1_speed_20150101_d0p494025m"
    limitations = analytics.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        raise ManifestError("analytics limitations are missing")
    properties: dict[str, Any] = {
        "product_id": "GLOBAL_MULTIYEAR_PHY_001_030",
        "source_model": "GLORYS12V1",
        "processing_type": "reanalysis",
        "product_type": SAMPLE_PRODUCT_TYPE,
        "analytics_version": _require_text(analytics, "analytics_version"),
        "source_conversion_manifest": SOURCE_MANIFEST.as_posix(),
        "source_conversion_manifest_sha256": conversion_manifest_sha256,
        "source_config_hash": _require_text(analytics, "config_hash"),
        "derived_checksum": _require_text(product, "sha256"),
        "reference_period": f"{reference_years[0]}-{reference_years[-1]}",
        "period_start": period_start,
        "period_end": period_end,
        "period_end_inclusive": False,
        "depth_m": 0.494025,
        "depth_label": "top_model_layer",
        "units": _require_text(product, "units"),
        "source_crs": _require_text(job, "crs"),
        "source_grid": dict(grid),
        "mask_method": "static_expected_ocean_mask:baseline_valid_pair_from_first_validated_frame",
        "mask_checksum": mask_checksum,
        "data_status": "validated_with_notes",
        "aoi_id": aoi_id,
        "is_reanalysis": True,
        "tides_included": False,
        "limitation": "; ".join(str(item) for item in limitations),
        "created_utc": created_utc,
        "source_time": _iso_z(_require_text(product, "time")),
        "source_path": _relative_path(root, source_path),
        "source_checksum": source_checksum,
        "plan_name": _require_text(product, "plan_name"),
        "job_id": _require_text(product, "job_id"),
        "method": "speed = sqrt(uo^2 + vo^2); source uo/vo joint mask preserved",
    }
    return {
        "schema_version": "gee-derived-asset-1.0",
        "asset_role": "derived",
        "name": f"{derived_collection}/speed/{stem}",
        "tilesets": [
            {
                "id": "derived",
                "sources": [{"uris": [f"gs://{gcs_bucket}/t6-004/derived/{derived_path.name}"]}],
            }
        ],
        "bands": [{"id": "speed", "tilesetBandIndex": 0, **_common_band()}],
        "properties": properties,
        "startTime": start_time,
        "endTime": end_time,
    }


def _validate_manifest(manifest: Mapping[str, Any], role: str) -> None:
    expected_keys = {"schema_version", "asset_role", "name", "tilesets", "bands", "properties", "startTime", "endTime"}
    if set(manifest) != expected_keys:
        raise ManifestError(f"{role} manifest top-level keys do not match schema contract")
    if manifest.get("asset_role") != role:
        raise ManifestError(f"manifest role mismatch: expected {role}")
    properties = manifest.get("properties")
    if not isinstance(properties, dict):
        raise ManifestError(f"{role} manifest properties must be an object")
    if properties.get("period_end_inclusive") is not False:
        raise ManifestError(f"{role} period end must be exclusive")
    if not re.fullmatch(r"[A-Fa-f0-9]{64}", str(properties.get("source_checksum", ""))):
        raise ManifestError("source checksum must be SHA-256")
    if role == "derived" and not re.fullmatch(r"[A-Fa-f0-9]{64}", str(properties.get("derived_checksum", ""))):
        raise ManifestError("derived checksum must be SHA-256")
    grid = properties.get("source_grid")
    if not isinstance(grid, dict) or set(grid) != {"crs", "transform", "shape"}:
        raise ManifestError(f"{role} source grid is incomplete")
    if len(grid["transform"]) != 6 or len(grid["shape"]) != 2:
        raise ManifestError(f"{role} source grid dimensions are invalid")


def build_sample_manifests(
    root: str | Path,
    *,
    gcs_bucket: str,
    created_utc: str,
) -> dict[str, dict[str, Any]]:
    """Build one source and one derived manifest from local Stage 5 evidence."""

    root_path = Path(root).resolve()
    bucket = _validate_bucket(gcs_bucket)
    created = _validate_created_utc(created_utc)
    conversion_path = root_path / SOURCE_MANIFEST
    validated_path = root_path / VALIDATED_MANIFEST
    analytics_path = root_path / ANALYTICS_MANIFEST
    naming = _read_json(root_path / ASSET_NAMING)
    conversion = _read_json(conversion_path)
    validated = _read_json(validated_path)
    analytics = _read_json(analytics_path)
    job = _find_job(conversion)
    validated_entry = _find_validated_entry(validated)
    output = _find_output(job)
    product = _find_product(analytics)
    source_path = _repo_path(root_path, _require_text(output, "path"))
    derived_path = _repo_path(root_path, _require_text(product, "path"))
    if not source_path.is_file() or not derived_path.is_file():
        raise ManifestError("sample source or derived raster is missing")
    if _sha256(source_path) != _require_text(output, "sha256"):
        raise ManifestError("sample source raster checksum does not match conversion manifest")
    if _sha256(derived_path) != _require_text(product, "sha256"):
        raise ManifestError("sample derived raster checksum does not match analytics manifest")
    source_grid = read_geotiff_grid(source_path)
    derived_grid = read_geotiff_grid(derived_path)
    if source_grid != derived_grid:
        raise ManifestError("source and derived sample grids differ")
    aoi = analytics.get("aoi")
    aoi_id = _require_text(aoi, "aoi_id") if isinstance(aoi, dict) else ""
    if not aoi_id:
        raise ManifestError("analytics AOI ID is missing")
    mask_checksum = _find_mask(analytics)
    source_manifest = _source_manifest(
        root=root_path,
        naming=naming,
        job=job,
        validated_entry=validated_entry,
        output=output,
        grid=source_grid,
        gcs_bucket=bucket,
        created_utc=created,
        aoi_id=aoi_id,
    )
    derived_manifest = _derived_manifest(
        root=root_path,
        naming=naming,
        job=job,
        output=output,
        product=product,
        grid=source_grid,
        mask_checksum=mask_checksum,
        conversion_manifest_sha256=_sha256(conversion_path),
        analytics=analytics,
        gcs_bucket=bucket,
        created_utc=created,
        aoi_id=aoi_id,
    )
    _validate_manifest(source_manifest, "source")
    _validate_manifest(derived_manifest, "derived")
    return {"source": source_manifest, "derived": derived_manifest}


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise ManifestError(f"cannot write manifest atomically: {path}") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def write_sample_manifests(
    root: str | Path,
    *,
    output_dir: str | Path,
    gcs_bucket: str,
    created_utc: str,
) -> dict[str, Any]:
    """Write T6-004 sample manifests and an index without upload commands."""

    root_path = Path(root).resolve()
    destination = Path(output_dir)
    if not destination.is_absolute():
        destination = root_path / destination
    destination = destination.resolve()
    try:
        destination.relative_to(root_path)
    except ValueError as exc:
        raise ManifestError("output directory must remain inside the repository") from exc
    samples = build_sample_manifests(root_path, gcs_bucket=gcs_bucket, created_utc=created_utc)
    filenames = {
        "source": "source_daily_jfm_20150101.json",
        "derived": "derived_speed_daily_jfm_20150101.json",
    }
    destination.mkdir(parents=True, exist_ok=True)
    for filename in (*filenames.values(), "manifest_index.json"):
        if (destination / filename).exists():
            raise ManifestError(f"refusing to overwrite existing T6-004 artifact: {destination / filename}")
    records = []
    for role in ("source", "derived"):
        path = destination / filenames[role]
        _atomic_write_json(path, samples[role])
        records.append({"role": role, "path": _relative_path(root_path, path), "sha256": _sha256(path)})
    index = {
        "status": "PASS_WITH_NOTES",
        "stage": "T6-004",
        "sample_count": len(records),
        "created_utc": created_utc,
        "gcs_bucket": gcs_bucket,
        "manifests": records,
        "limitations": [
            "GCS bucket is a sample configuration value; its existence was not checked.",
            "No Earth Engine authentication, upload, export, or cloud task was executed.",
            "T6-005 remains a separate approved upload gate.",
        ],
    }
    _atomic_write_json(destination / "manifest_index.json", index)
    return index


__all__ = [
    "ManifestError",
    "build_sample_manifests",
    "read_geotiff_grid",
    "write_sample_manifests",
]
