"""Build the offline T6-007/T6-008 publish-selection manifest.

The manifest is a checked selection inventory, not an upload plan.  It reads
only Stage 5 manifests and local GeoTIFF files.  It never authenticates,
contacts GCS/Earth Engine, or creates cloud tasks.
"""

from __future__ import annotations

import calendar
import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

try:  # Supports both ``python -m`` imports and direct script execution.
    from .gee_manifest import ManifestError, _atomic_write_json, _read_json, _repo_path, _relative_path
except ImportError:  # pragma: no cover - exercised by the CLI entry point
    from gee_manifest import ManifestError, _atomic_write_json, _read_json, _repo_path, _relative_path


CONVERSION_MANIFEST = Path("outputs/manifests/stage_5_conversion_manifest.json")
CONVERSION_AUDIT = Path("outputs/manifests/stage_5_audit_manifest.json")
COMPARISON_MANIFEST = Path("outputs/manifests/stage_5_collection_comparison.json")
ANALYTICS_MANIFEST = Path("outputs/manifests/stage_5_analytics_manifest.json")
ANALYTICS_AUDIT = Path("outputs/manifests/stage_5_analytics_audit.json")
ASSET_NAMING = Path("config/asset_naming.json")

SOURCE_REASON = {
    "monthly_all": (
        "Core source collection for FR-GEE-01/02: complete monthly 2015-2025 "
        "coverage enables date filtering and monthly research without missing frames."
    ),
    "daily_jfm": (
        "Core source collection for the approved 993-frame JFM MVP and FR-GEE-01/02/03; "
        "the limited seasonal scope avoids activating daily_full."
    ),
}
DERIVED_REASON = {
    "speed": (
        "Core precomputed speed for FR-GEE-07 and the implementation reader; "
        "it preserves the validated Stage 5 speed result and avoids 11-year recomputation."
    ),
    "monthly_climatology_speed": (
        "Core precomputed monthly climatology for FR-GEE-07; it supports the 11-year "
        "summary view without interactive collection-wide reduction."
    ),
    "jfm_climatology_speed": (
        "Core precomputed JFM climatology for FR-GEE-07 and the approved seasonal MVP; "
        "it avoids interactive recomputation across 993 daily frames."
    ),
}


def _read_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ManifestError(f"cannot hash selected local file: {path}") from exc
    return digest.hexdigest()


def _text(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ManifestError(f"required manifest field {key!r} is missing")
    return value


def _sha256_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Fa-f0-9]{64}", value):
        raise ManifestError(f"{label} must be a SHA-256 checksum")
    return value


def _status(manifest: Mapping[str, Any], label: str) -> None:
    status = manifest.get("status")
    if status not in {"PASS", "PASS_WITH_NOTES"}:
        raise ManifestError(f"{label} is not passing: {status!r}")


def _input_record(root: Path, path: Path, manifest: Mapping[str, Any]) -> dict[str, Any]:
    _status(manifest, path.as_posix())
    return {
        "path": path.as_posix(),
        "sha256": _read_sha256(root / path),
        "status": manifest["status"],
    }


def _period(value: str, plan_name: str) -> tuple[str, str]:
    parsed = datetime.fromisoformat(value)
    if plan_name == "monthly_all":
        days = calendar.monthrange(parsed.year, parsed.month)[1]
        end = parsed + timedelta(days=days)
    elif plan_name == "daily_jfm":
        end = parsed + timedelta(days=1)
    else:
        raise ManifestError(f"unsupported period plan: {plan_name}")
    return (
        parsed.isoformat(timespec="seconds") + "Z",
        end.isoformat(timespec="seconds") + "Z",
    )


def _asset_name(stem: str, value: str) -> str:
    parsed = datetime.fromisoformat(value)
    if stem == "daily":
        return f"glorys12v1_d_{parsed:%Y%m%d}_d0p494025m"
    if stem == "monthly":
        return f"glorys12v1_m_{parsed:%Y%m}_d0p494025m"
    raise ManifestError(f"unsupported source collection stem: {stem}")


def _local_file(root: Path, raw_path: str, expected_sha: Any, label: str) -> tuple[str, int]:
    path = _repo_path(root, raw_path)
    if not path.is_file():
        raise ManifestError(f"{label} local file is missing: {path}")
    actual = _read_sha256(path)
    expected = _sha256_text(expected_sha, f"{label} checksum")
    if actual != expected:
        raise ManifestError(f"{label} checksum differs from Stage 5 manifest: {path}")
    return _relative_path(root, path), path.stat().st_size


def _source_asset(
    *, root: Path, naming: Mapping[str, Any], job: Mapping[str, Any], output: Mapping[str, Any]
) -> dict[str, Any]:
    plan_name = _text(job, "plan_name")
    if plan_name not in SOURCE_REASON:
        raise ManifestError(f"unsupported source plan: {plan_name}")
    collection_key = "daily_jfm_collection" if plan_name == "daily_jfm" else "monthly_collection"
    collection = _text(naming["paths"], collection_key)
    stem = "daily" if plan_name == "daily_jfm" else "monthly"
    time_value = _text(output, "time")
    start_time, end_time = _period(time_value, plan_name)
    relative_path, size_bytes = _local_file(root, _text(output, "path"), output.get("sha256"), "source")
    expected_bands = ["uo", "vo"]
    if job.get("bands") != expected_bands or job.get("dtype") != "float32":
        raise ManifestError(f"source schema contract differs for {job.get('job_id')}")
    if job.get("crs") != "EPSG:4326" or job.get("nodata") != -9999.0 or job.get("resampling") != "none":
        raise ManifestError(f"source grid/mask contract differs for {job.get('job_id')}")
    return {
        "asset_role": "source",
        "selection_reason": SOURCE_REASON[plan_name],
        "plan_name": plan_name,
        "job_id": _text(job, "job_id"),
        "time": time_value,
        "startTime": start_time,
        "endTime": end_time,
        "source_path": relative_path,
        "source_sha256": _sha256_text(output.get("sha256"), "source"),
        "size_bytes": size_bytes,
        "bands": expected_bands,
        "dtype": job["dtype"],
        "crs": job["crs"],
        "nodata": job["nodata"],
        "resampling": job["resampling"],
        "target_asset_id": f"{collection}/{_asset_name(stem, time_value)}",
    }


def _speed_asset(*, root: Path, naming: Mapping[str, Any], product: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    plan_name = _text(product, "plan_name")
    if plan_name not in SOURCE_REASON:
        raise ManifestError(f"speed product has unsupported plan: {plan_name}")
    relative_path, size_bytes = _local_file(root, _text(product, "path"), product.get("sha256"), "derived speed")
    source_path = _relative_path(root, _repo_path(root, _text(product, "source_path")))
    if source_path != source["source_path"]:
        raise ManifestError(f"speed/source path mismatch for {product.get('time')}")
    time_value = _text(product, "time")
    if time_value != source["time"]:
        raise ManifestError(f"speed/source time mismatch for {time_value}")
    start_time, end_time = _period(time_value, plan_name)
    speed_collection = f"{_text(naming['paths'], 'derived')}/speed/{plan_name}"
    parsed = datetime.fromisoformat(time_value)
    stem = f"glorys12v1_speed_{parsed:%Y%m%d}_d0p494025m"
    return {
        "asset_role": "derived",
        "selection_reason": DERIVED_REASON["speed"],
        "product_type": "speed",
        "plan_name": plan_name,
        "job_id": _text(product, "job_id"),
        "time": time_value,
        "startTime": start_time,
        "endTime": end_time,
        "source_path": source_path,
        "source_sha256": source["source_sha256"],
        "derived_path": relative_path,
        "derived_sha256": _sha256_text(product.get("sha256"), "derived speed"),
        "size_bytes": size_bytes,
        "units": _text(product, "units"),
        "target_asset_id": f"{speed_collection}/{stem}",
    }


def _summary_asset(*, root: Path, naming: Mapping[str, Any], product: Mapping[str, Any]) -> dict[str, Any]:
    product_type = _text(product, "product_type")
    if product_type not in {"monthly_climatology_speed", "jfm_climatology_speed"}:
        raise ManifestError(f"unsupported selected summary product: {product_type}")
    relative_path, size_bytes = _local_file(root, _text(product, "path"), product.get("sha256"), product_type)
    if product_type == "monthly_climatology_speed":
        month = product.get("month")
        if not isinstance(month, int) or not 1 <= month <= 12:
            raise ManifestError("monthly climatology month is invalid")
        target = f"{_text(naming['paths'], 'derived')}/monthly_climatology/glorys12v1_monthly_climatology_speed_{month:02d}_d0p494025m"
    else:
        target = f"{_text(naming['paths'], 'derived')}/jfm_climatology/glorys12v1_jfm_climatology_speed_d0p494025m"
    return {
        "asset_role": "derived",
        "selection_reason": DERIVED_REASON[product_type],
        "product_type": product_type,
        "reference_period": _text(product, "reference_period"),
        **({"month": product["month"]} if product_type == "monthly_climatology_speed" else {}),
        "derived_path": relative_path,
        "derived_sha256": _sha256_text(product.get("sha256"), product_type),
        "size_bytes": size_bytes,
        "units": "m s-1",
        "target_asset_id": target,
    }


def _deferred(products: list[Mapping[str, Any]], analytics: Mapping[str, Any]) -> list[dict[str, Any]]:
    reasons = {
        "speed_anomaly": (
            "Deferred until a GEE anomaly reader and baseline display contract are approved; "
            "local Stage 5 products remain preserved and traceable."
        ),
        "exploratory_trend_slope": (
            "Deferred because the product is explicitly exploratory and no GEE reader/UI "
            "requirement exists yet; no inferential or causal claim is permitted."
        ),
    }
    result = []
    counts: dict[str, int] = {}
    for product in products:
        product_type = _text(product, "product_type")
        if product_type in reasons:
            counts[product_type] = counts.get(product_type, 0) + 1
    for product_type, reason in reasons.items():
        result.append({"category": product_type, "local_count": counts.get(product_type, 0), "reason": reason})
    masks = analytics.get("masks")
    result.append({
        "category": "static_expected_ocean_masks",
        "local_count": len(masks) if isinstance(masks, list) else 0,
        "reason": "Supporting QC artifacts remain local until a GEE mask/support-asset contract and geometry policy are approved.",
    })
    return result


def build_publish_manifest(root: str | Path, *, created_utc: str) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", created_utc):
        raise ManifestError("created_utc must be an explicit UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(created_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManifestError("created_utc is not a valid timestamp") from exc

    conversion = _read_json(root_path / CONVERSION_MANIFEST)
    conversion_audit = _read_json(root_path / CONVERSION_AUDIT)
    comparison = _read_json(root_path / COMPARISON_MANIFEST)
    analytics = _read_json(root_path / ANALYTICS_MANIFEST)
    analytics_audit = _read_json(root_path / ANALYTICS_AUDIT)
    naming = _read_json(root_path / ASSET_NAMING)
    for manifest, label in (
        (conversion, "conversion manifest"),
        (conversion_audit, "conversion audit"),
        (comparison, "conversion comparison"),
        (analytics_audit, "analytics audit"),
    ):
        _status(manifest, label)
    if conversion.get("timestep_count") != 1125 or conversion.get("expected_timestep_count") != 1125:
        raise ManifestError("conversion manifest does not contain the approved 1,125 timestep MVP")
    if conversion_audit.get("checked_output_count") != 1125:
        raise ManifestError("conversion audit does not cover 1,125 outputs")
    if comparison.get("file_count") != 1125:
        raise ManifestError("conversion comparison does not cover 1,125 outputs")
    if analytics.get("frame_count") != 1125 or analytics_audit.get("product_count") != 2264:
        raise ManifestError("analytics evidence counts do not match Stage 5 contract")

    jobs = conversion.get("jobs")
    if not isinstance(jobs, list) or len(jobs) != 165:
        raise ManifestError("conversion manifest must contain exactly 165 jobs")
    source_assets: list[dict[str, Any]] = []
    source_by_path: dict[str, dict[str, Any]] = {}
    for job in jobs:
        if not isinstance(job, dict):
            raise ManifestError("conversion job must be an object")
        outputs = job.get("outputs")
        if not isinstance(outputs, list):
            raise ManifestError(f"outputs missing for {job.get('job_id')}")
        for output in outputs:
            if not isinstance(output, dict):
                raise ManifestError("conversion output must be an object")
            asset = _source_asset(root=root_path, naming=naming, job=job, output=output)
            source_assets.append(asset)
            source_by_path[asset["source_path"]] = asset
    source_assets.sort(key=lambda item: (item["time"], item["plan_name"]))
    if len(source_assets) != 1125 or len(source_by_path) != 1125:
        raise ManifestError("source selection is not exactly 1,125 unique frames")

    products = analytics.get("products")
    if not isinstance(products, list):
        raise ManifestError("analytics products must be a list")
    derived_assets: list[dict[str, Any]] = []
    for product in products:
        if not isinstance(product, dict):
            raise ManifestError("analytics product must be an object")
        product_type = product.get("product_type")
        if product_type == "speed":
            normalized_source_path = _relative_path(root_path, _repo_path(root_path, _text(product, "source_path")))
            source = source_by_path.get(normalized_source_path)
            if source is None:
                raise ManifestError(f"speed source is not in selected source collection: {product.get('time')}")
            derived_assets.append(_speed_asset(root=root_path, naming=naming, product=product, source=source))
        elif product_type in {"monthly_climatology_speed", "jfm_climatology_speed"}:
            derived_assets.append(_summary_asset(root=root_path, naming=naming, product=product))
    derived_assets.sort(key=lambda item: (item["product_type"], item.get("time", ""), item.get("month", 0)))
    if len([a for a in derived_assets if a["product_type"] == "speed"]) != 1125:
        raise ManifestError("selected speed products are not exactly 1,125")
    if len([a for a in derived_assets if a["product_type"] == "monthly_climatology_speed"]) != 12:
        raise ManifestError("selected monthly climatology products are not exactly 12")
    if len([a for a in derived_assets if a["product_type"] == "jfm_climatology_speed"]) != 1:
        raise ManifestError("selected JFM climatology product is not exactly 1")

    input_paths = [CONVERSION_MANIFEST, CONVERSION_AUDIT, COMPARISON_MANIFEST, ANALYTICS_MANIFEST, ANALYTICS_AUDIT]
    inputs = [_input_record(root_path, path, _read_json(root_path / path)) for path in input_paths]
    return {
        "schema_version": "gee-publish-selection-1.0",
        "status": "PASS_WITH_NOTES",
        "stage": "T6-007/T6-008",
        "created_utc": created_utc,
        "project_id": _text(naming, "earth_engine_project_id"),
        "asset_root": _text(naming, "earth_engine_asset_root"),
        "selection_policy": {
            "mode": "core_implementation_publish_on_demand",
            "source": "all approved Stage 5 MVP frames: 132 monthly_all and 993 daily_jfm",
            "derived": "all speed frames plus 12 monthly climatologies and 1 JFM climatology",
            "daily_full": "disabled",
            "reason": "The selected set supports source reading, limited-period analysis, and precomputed summaries while deferring products without an approved GEE reader contract.",
        },
        "inputs": inputs,
        "source": {
            "selected_count": len(source_assets),
            "groups": {
                "monthly_all": {"count": 132, "reason": SOURCE_REASON["monthly_all"]},
                "daily_jfm": {"count": 993, "reason": SOURCE_REASON["daily_jfm"]},
            },
            "assets": source_assets,
        },
        "derived": {
            "selected_count": len(derived_assets),
            "groups": {
                "speed": {"count": 1125, "reason": DERIVED_REASON["speed"]},
                "monthly_climatology_speed": {"count": 12, "reason": DERIVED_REASON["monthly_climatology_speed"]},
                "jfm_climatology_speed": {"count": 1, "reason": DERIVED_REASON["jfm_climatology_speed"]},
            },
            "assets": derived_assets,
        },
        "deferred": _deferred(products, analytics),
        "staging": {
            "status": "NOT_CONFIGURED",
            "gcs_bucket": None,
            "upload_commands_generated": False,
            "note": "A bucket, billing decision, and upload approval are required before T6-009/T6-010.",
        },
        "limitations": [
            "This is an offline selection manifest; no GCS or Earth Engine existence check was performed.",
            "No authentication, upload, export, ACL/IAM mutation, or cloud task was executed.",
            "Selected GeoTIFFs remain local and ignored by Git; checksums are verified against Stage 5 manifests.",
            "Target asset IDs are collision-safe plan-scoped names for bulk speed assets; the T6-006 canonical sample remains a separately validated legacy alias.",
            "Status is PASS_WITH_NOTES because cloud staging, upload, and runtime reconciliation are downstream T6-009..T6-012.",
        ],
    }


def write_publish_manifest(root: str | Path, *, output_dir: str | Path, created_utc: str) -> dict[str, Any]:
    root_path = Path(root).resolve()
    destination = Path(output_dir)
    if not destination.is_absolute():
        destination = root_path / destination
    destination = destination.resolve()
    try:
        destination.relative_to(root_path)
    except ValueError as exc:
        raise ManifestError("output directory must remain inside the repository") from exc
    path = destination / "t6_007_t6_008_publish_manifest.json"
    if path.exists():
        raise ManifestError(f"refusing to overwrite existing publish manifest: {path}")
    manifest = build_publish_manifest(root_path, created_utc=created_utc)
    _atomic_write_json(path, manifest)
    return {"manifest": _relative_path(root_path, path), "sha256": _read_sha256(path), **{k: manifest[k] for k in ("status", "stage")}}


__all__ = ["build_publish_manifest", "write_publish_manifest"]
