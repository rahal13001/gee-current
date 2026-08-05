"""Offline analytics and precomputed products for the validated Stage 5 collection.

The module consumes only the local GeoTIFF collection produced by T5-008.  It
keeps missing pixels as missing, records every method choice, and applies only
the approved derived P90 threshold and static expected-ocean mask.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import rasterio
from rasterio.transform import Affine

from python.checksum import sha256_file
from python.common.constants import DIRECTION_CONVENTION
from python.common.descriptive_statistics import summary_statistics
from python.conversion import PIPELINE_VERSION, _atomic_write_json


ANALYTICS_VERSION = "stage5-analytics-1.0"
EARTH_RADIUS_M = 6_371_008.8
ZERO_EPSILON_MPS = 1e-6
MINIMUM_VALID_AREA_FRACTION = 0.95
SECTOR_LABELS = (
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
)


class AnalyticsError(ValueError):
    """Raised when analytics inputs or method contracts are invalid."""


@dataclass(frozen=True)
class FrameRecord:
    """One converted source frame with deterministic provenance."""

    plan_name: str
    job_id: str
    time: str
    source_path: Path
    speed_path: Path


def _quantile(values: Sequence[float], probability: float, percentile_method: str) -> float:
    """Return a deterministic quantile using the approved interpolation method."""

    if not values:
        raise AnalyticsError("cannot calculate a quantile from an empty series")
    return float(np.quantile(np.asarray(values, dtype=np.float64), probability, method=percentile_method))


def _spatial_mean_vector(
    u: np.ndarray,
    v: np.ndarray,
    area: np.ndarray,
    minimum_valid_area_fraction: float,
    expected_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """Compute an area-weighted vector and reject unsupported timesteps."""

    if expected_mask is None:
        expected_mask = np.ones(u.shape, dtype=bool)
    if expected_mask.shape != u.shape:
        raise AnalyticsError("expected mask shape must match vector arrays")
    valid = np.isfinite(u) & np.isfinite(v) & np.isfinite(area) & expected_mask
    expected_area = float(np.nansum(area[expected_mask]))
    valid_area = float(np.nansum(area[valid]))
    fraction = valid_area / expected_area if expected_area else 0.0
    if fraction < minimum_valid_area_fraction:
        return {
            "accepted": False,
            "mean_u": None,
            "mean_v": None,
            "resultant_speed": None,
            "resultant_direction": None,
            "valid_area_fraction": fraction,
            "valid_pixel_count": int(valid.sum()),
        }
    if not valid.any():
        return {
            "accepted": False,
            "mean_u": None,
            "mean_v": None,
            "resultant_speed": None,
            "resultant_direction": None,
            "valid_area_fraction": fraction,
            "valid_pixel_count": 0,
        }
    mean_u = float(np.average(u[valid], weights=area[valid]))
    mean_v = float(np.average(v[valid], weights=area[valid]))
    return {
        "accepted": True,
        "mean_u": mean_u,
        "mean_v": mean_v,
        "resultant_speed": float(np.hypot(mean_u, mean_v)),
        "resultant_direction": resultant_direction_degrees(mean_u, mean_v),
        "valid_area_fraction": fraction,
        "valid_pixel_count": int(valid.sum()),
    }


def _speed_bin_definitions(
    values: Sequence[float],
    threshold: float,
    percentile_method: str,
) -> list[dict[str, Any]]:
    """Create global AOI quantile bins and merge duplicate edges."""

    quantiles = {
        "p25": _quantile(values, 0.25, percentile_method),
        "p50": _quantile(values, 0.50, percentile_method),
        "p75": _quantile(values, 0.75, percentile_method),
        "p90": threshold,
    }
    definitions: list[dict[str, Any]] = [
        {"speed_bin": "ZERO", "lower": None, "upper": ZERO_EPSILON_MPS},
    ]
    edges = [ZERO_EPSILON_MPS, quantiles["p25"], quantiles["p50"], quantiles["p75"], quantiles["p90"]]
    labels = ["BIN_1", "BIN_2", "BIN_3", "BIN_4", "BIN_5"]
    lower = ZERO_EPSILON_MPS
    for label, edge in zip(labels, edges[1:]):
        if edge <= lower:
            continue
        definitions.append({"speed_bin": label, "lower": lower, "upper": edge})
        lower = edge
    definitions.append({"speed_bin": "BIN_5", "lower": lower, "upper": None})
    # Keep the terminal bin unique when P90 is itself at or below epsilon.
    result: list[dict[str, Any]] = []
    seen: set[tuple[float | None, float | None]] = set()
    for item in definitions:
        key = (item["lower"], item["upper"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _speed_bin_for_value(value: float, definitions: Sequence[Mapping[str, Any]]) -> str:
    """Assign a speed to a lower-inclusive/upper-inclusive project bin."""

    if value <= ZERO_EPSILON_MPS:
        return "ZERO"
    for item in definitions:
        lower = item.get("lower")
        upper = item.get("upper")
        if item["speed_bin"] == "ZERO":
            continue
        if (lower is None or value > float(lower)) and (upper is None or value <= float(upper)):
            return str(item["speed_bin"])
    raise AnalyticsError(f"speed value was not assigned to a bin: {value}")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    """Write a deterministic CSV atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _write_current_rose_svg(
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    bin_definitions: Sequence[Mapping[str, Any]],
) -> None:
    """Write a dependency-free stacked polar current-rose SVG."""

    colors = ("#64748b", "#38bdf8", "#22c55e", "#facc15", "#fb923c", "#ef4444")
    width, height = 720, 620
    cx, cy, radius = 300, 315, 210
    totals: dict[tuple[str, str], float] = {}
    for row in rows:
        totals[(str(row["direction_sector"]), str(row["speed_bin"]))] = float(row["frequency_percentage"])
    max_freq = max((sum(totals.get((label, item["speed_bin"]), 0.0) for item in bin_definitions) for label in SECTOR_LABELS), default=1.0)
    scale = radius / max(max_freq, 1.0)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="24" y="30" font-family="sans-serif" font-size="18" font-weight="bold">Current rose — {escape(str(summary["analysis_plan_id"]))} — menuju</text>',
        '<text x="24" y="52" font-family="sans-serif" font-size="12">Frekuensi terhadap timestep valid; zero/calm numerik dilaporkan terpisah</text>',
    ]
    for grid in (0.25, 0.50, 0.75, 1.0):
        r = radius * grid
        elements.append(f'<circle cx="{cx}" cy="{cy}" r="{r:.2f}" fill="none" stroke="#cbd5e1"/>')
    for index, label in enumerate(SECTOR_LABELS):
        angle = math.radians(index * 22.5)
        x = cx + (radius + 24) * math.sin(angle)
        y = cy - (radius + 24) * math.cos(angle)
        elements.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" font-family="sans-serif" font-size="11">{label}</text>')
        radial = 0.0
        for bin_index, item in enumerate(bin_definitions):
            value = totals.get((label, str(item["speed_bin"])), 0.0) * scale
            if value <= 0:
                continue
            x1 = cx + radial * math.sin(angle)
            y1 = cy - radial * math.cos(angle)
            radial += value
            x2 = cx + radial * math.sin(angle)
            y2 = cy - radial * math.cos(angle)
            elements.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{colors[bin_index % len(colors)]}" stroke-width="10"/>')
    legend_y = 100
    for index, item in enumerate(bin_definitions):
        label = str(item["speed_bin"])
        elements.append(f'<rect x="520" y="{legend_y + index * 24}" width="14" height="14" fill="{colors[index % len(colors)]}"/>')
        elements.append(f'<text x="540" y="{legend_y + 12 + index * 24}" font-family="sans-serif" font-size="11">{escape(label)}</text>')
    elements.extend([
        f'<text x="520" y="280" font-family="sans-serif" font-size="11">valid={summary["valid_count"]}; zero={summary["zero_count"]}; missing={summary["missing_count"]}</text>',
        f'<text x="520" y="300" font-family="sans-serif" font-size="11">P90={float(summary["threshold_global_p90_mps"]):.6f} m s-1</text>',
        f'<text x="520" y="320" font-family="sans-serif" font-size="11">depth={escape(str(summary["depth_m"]))} m</text>',
        '<text x="24" y="590" font-family="sans-serif" font-size="11">Model limitation: static expected-ocean mask is baseline valid-pair mask; exact water polygon/zones are not supplied.</text>',
        '</svg>',
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(elements), encoding="utf-8")


def _finite_array(values: np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim < 1:
        raise AnalyticsError(f"{label} must be an array")
    return array


def speed_array(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Return elementwise scalar speed while preserving the joint NaN mask."""

    u_array = _finite_array(u, "u")
    v_array = _finite_array(v, "v")
    if u_array.shape != v_array.shape:
        raise AnalyticsError("u and v shapes must match")
    valid = np.isfinite(u_array) & np.isfinite(v_array)
    result = np.full(u_array.shape, np.nan, dtype=np.float64)
    result[valid] = np.hypot(u_array[valid], v_array[valid])
    return result


def mean_components_array(u: np.ndarray, v: np.ndarray) -> tuple[float, float, int]:
    """Return valid-count-aware mean u, mean v, and paired valid count."""

    u_array = _finite_array(u, "u")
    v_array = _finite_array(v, "v")
    if u_array.shape != v_array.shape:
        raise AnalyticsError("u and v shapes must match")
    valid = np.isfinite(u_array) & np.isfinite(v_array)
    count = int(valid.sum())
    if count == 0:
        raise AnalyticsError("no paired valid vectors")
    return float(u_array[valid].mean()), float(v_array[valid].mean()), count


def resultant_direction_degrees(mean_u: float, mean_v: float) -> float | None:
    """Return toward-bearing degrees clockwise from north; zero vector is null."""

    if not math.isfinite(mean_u) or not math.isfinite(mean_v):
        raise AnalyticsError("mean components must be finite")
    if mean_u == 0.0 and mean_v == 0.0:
        return None
    return float(math.degrees(math.atan2(mean_u, mean_v)) % 360.0)


def direction_sector_array(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Return 16 toward-direction sector indices with north-centered wrapping."""

    u_array = _finite_array(u, "u")
    v_array = _finite_array(v, "v")
    if u_array.shape != v_array.shape:
        raise AnalyticsError("u and v shapes must match")
    valid = np.isfinite(u_array) & np.isfinite(v_array) & ((u_array != 0.0) | (v_array != 0.0))
    result = np.full(u_array.shape, -1, dtype=np.int8)
    bearings = np.degrees(np.arctan2(u_array[valid], v_array[valid])) % 360.0
    result[valid] = np.floor(((bearings + 11.25) % 360.0) / 22.5).astype(np.int8)
    return result


def frame_statistics(
    u: np.ndarray,
    v: np.ndarray,
    *,
    ddof: int,
    percentile_method: str,
) -> dict[str, Any]:
    """Compute scalar/vector statistics and a dominant 16-sector direction."""

    u_array = _finite_array(u, "u")
    v_array = _finite_array(v, "v")
    if u_array.shape != v_array.shape:
        raise AnalyticsError("u and v shapes must match")
    valid = np.isfinite(u_array) & np.isfinite(v_array)
    count = int(valid.sum())
    if count == 0:
        raise AnalyticsError("frame has no paired valid vectors")
    speeds = speed_array(u_array, v_array)[valid]
    speed_stats = summary_statistics(speeds.tolist(), ddof=ddof, percentile_method=percentile_method)
    mean_u = float(u_array[valid].mean())
    mean_v = float(v_array[valid].mean())
    resultant = float(np.hypot(mean_u, mean_v))
    direction = resultant_direction_degrees(mean_u, mean_v)
    persistence = None if speed_stats["mean"] == 0 else resultant / float(speed_stats["mean"])
    sectors = direction_sector_array(u_array, v_array)[valid]
    sector_counts = np.bincount(sectors[sectors >= 0], minlength=16)
    dominant_index = int(np.argmax(sector_counts)) if int(sector_counts.sum()) else None
    result: dict[str, Any] = dict(speed_stats)
    result.update(
        {
            "mean_u": mean_u,
            "mean_v": mean_v,
            "resultant_speed": resultant,
            "resultant_direction": direction,
            "persistence_index": persistence,
            "direction_convention": DIRECTION_CONVENTION,
            "dominant_direction_sector": dominant_index,
            "dominant_direction_label": SECTOR_LABELS[dominant_index] if dominant_index is not None else None,
            "direction_sector_counts": [int(value) for value in sector_counts],
            "valid_pixel_count": count,
            "total_pixel_count": int(u_array.size),
            "valid_percentage": 100.0 * count / u_array.size,
        }
    )
    return result


def _atomic_write_raster(path: Path, array: np.ndarray, profile: Mapping[str, Any], tags: Mapping[str, str]) -> None:
    """Write a single-band float32 derived raster atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    output = np.where(np.isfinite(array), array, -9999.0).astype("float32", copy=False)
    raster_profile = dict(profile)
    raster_profile.update(
        count=1,
        dtype="float32",
        nodata=-9999.0,
        compress="deflate",
        predictor=2,
        tiled=False,
    )
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
        with rasterio.open(temporary, "w", **raster_profile) as destination:
            destination.write(output, 1)
            destination.set_band_description(1, str(tags.get("band_name", "derived")))
            destination.update_tags(**{key: str(value) for key, value in tags.items()})
        os.replace(temporary, path)
    except (OSError, rasterio.errors.RasterioError) as exc:
        raise AnalyticsError(f"cannot write derived raster: {path}") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _read_vector(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Read a source two-band raster and return arrays plus its profile."""

    try:
        with rasterio.open(path) as source:
            if source.count != 2 or source.dtypes != ("float32", "float32"):
                raise AnalyticsError(f"source raster schema mismatch: {path}")
            data = source.read(masked=True)
            arrays = data.filled(np.nan).astype(np.float64)
            return arrays[0], arrays[1], source.profile
    except rasterio.errors.RasterioError as exc:
        raise AnalyticsError(f"cannot read source raster: {path}") from exc


def _mean_rasters(paths: Sequence[Path]) -> np.ndarray:
    """Compute a valid-count-aware raster mean without converting missing to zero."""

    if not paths:
        raise AnalyticsError("cannot average an empty raster group")
    total: np.ndarray | None = None
    count: np.ndarray | None = None
    for path in paths:
        with rasterio.open(path) as source:
            values = source.read(1, masked=True).filled(np.nan).astype(np.float64)
        valid = np.isfinite(values)
        if total is None:
            total = np.zeros(values.shape, dtype=np.float64)
            count = np.zeros(values.shape, dtype=np.int32)
        if values.shape != total.shape:
            raise AnalyticsError("raster shapes differ within a climatology group")
        total[valid] += values[valid]
        count[valid] += 1
    assert total is not None and count is not None
    result = np.full(total.shape, np.nan, dtype=np.float64)
    valid = count > 0
    result[valid] = total[valid] / count[valid]
    return result


def _linear_slope(years: Sequence[int], arrays: Sequence[np.ndarray]) -> np.ndarray:
    """Return exploratory per-pixel least-squares slope in units per year."""

    if len(years) != len(arrays) or len(years) < 2:
        raise AnalyticsError("trend requires at least two aligned years")
    stack = np.stack(arrays, axis=0).astype(np.float64)
    x = np.asarray(years, dtype=np.float64)
    x_centered = x - x.mean()
    valid = np.isfinite(stack)
    numerator = np.nansum(stack * x_centered[:, None, None], axis=0)
    denominator = np.sum(valid * (x_centered[:, None, None] ** 2), axis=0)
    result = np.full(stack.shape[1:], np.nan, dtype=np.float64)
    enough = valid.sum(axis=0) >= 2
    result[enough] = numerator[enough] / denominator[enough]
    return result


def _cell_area_m2(transform: Affine, height: int, width: int) -> np.ndarray:
    """Approximate EPSG:4326 cell area on a spherical Earth."""

    if transform.b != 0 or transform.d != 0:
        raise AnalyticsError("zonal area requires north-up unrotated raster")
    lat_centers = transform.f + (np.arange(height) + 0.5) * transform.e
    lon_width = math.radians(abs(transform.a))
    lat_half = math.radians(abs(transform.e)) / 2.0
    latitudes = np.radians(lat_centers)
    row_area = EARTH_RADIUS_M**2 * lon_width * (
        np.sin(latitudes + lat_half) - np.sin(latitudes - lat_half)
    )
    return np.repeat(np.abs(row_area)[:, None], width, axis=1)


def _safe_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AnalyticsError(f"cannot read JSON: {path}") from exc
    if not isinstance(value, dict):
        raise AnalyticsError(f"JSON root must be an object: {path}")
    return value


def _records_from_conversion_manifest(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    jobs = manifest.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise AnalyticsError("conversion manifest has no jobs")
    records: list[dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, dict):
            raise AnalyticsError("conversion job record is invalid")
        if job.get("status") not in {"PASS_WITH_NOTES", "RESUMED"}:
            raise AnalyticsError("conversion manifest contains a non-passing job")
        for output in job.get("outputs", []):
            if not isinstance(output, dict):
                raise AnalyticsError("conversion output record is invalid")
            records.append(
                {
                    "plan_name": str(job["plan_name"]),
                    "job_id": str(job["job_id"]),
                    "time": str(output["time"]),
                    "source_path": Path(str(output["path"])),
                }
            )
    if len(records) != int(manifest.get("expected_timestep_count", -1)):
        raise AnalyticsError("conversion manifest timestep inventory is inconsistent")
    return sorted(records, key=lambda item: (item["plan_name"], item["job_id"], item["time"]))


def run_collection_analytics(
    *,
    conversion_manifest_path: str | Path,
    output_root: str | Path,
    report_path: str | Path,
    config_hash_value: str,
    ddof: int = 0,
    percentile_method: str = "linear",
    analysis_period_path: str | Path = "config/analysis_period.json",
    study_area_path: str | Path = "config/study_area.json",
    statistics_path: str | Path = "config/statistics.json",
    depth_selection_path: str | Path = "config/depth_selection.json",
) -> dict[str, Any]:
    """Build speed products, climatologies, anomalies, trend, zonal table, and manifest."""

    if ddof not in (0, 1) or percentile_method != "linear":
        raise AnalyticsError("analytics baseline requires ddof 0/1 and percentile_method linear")
    conversion_path = Path(conversion_manifest_path).resolve()
    output_path = Path(output_root).resolve()
    conversion_manifest = _safe_json(conversion_path)
    records = _records_from_conversion_manifest(conversion_manifest)
    analysis_period = _safe_json(Path(analysis_period_path))
    study_area = _safe_json(Path(study_area_path))
    statistics_config = _safe_json(Path(statistics_path))
    depth_config = _safe_json(Path(depth_selection_path))
    if statistics_config.get("threshold_method") != "relative_high_current_threshold_global_p90":
        raise AnalyticsError("T5-017 requires the approved global AOI P90 method")
    if statistics_config.get("minimum_valid_area_fraction") != MINIMUM_VALID_AREA_FRACTION:
        raise AnalyticsError("T5-017/T5-019 require minimum valid area fraction 0.95")
    rose_config = statistics_config.get("current_rose")
    if not isinstance(rose_config, dict) or rose_config.get("sector_count") != 16:
        raise AnalyticsError("T5-019 requires 16 current-rose sectors")

    source_metadata: dict[str, dict[str, Any]] = {}
    source_manifest_reference = conversion_manifest.get("manifest")
    if source_manifest_reference:
        source_manifest_path = Path(str(source_manifest_reference))
        if source_manifest_path.is_file():
            source_manifest = _safe_json(source_manifest_path)
            for entry in source_manifest.get("entries", []):
                if isinstance(entry, dict) and entry.get("plan_name") not in source_metadata:
                    source_metadata[str(entry["plan_name"])] = entry

    products: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    speed_records: list[FrameRecord] = []
    speed_arrays: dict[str, np.ndarray] = {}
    profiles: dict[str, dict[str, Any]] = {}
    spatial_by_plan: dict[str, list[dict[str, Any]]] = {"daily_jfm": [], "monthly_all": []}
    static_expected_masks: dict[str, np.ndarray] = {}
    area_cache: dict[tuple[int, int, str], np.ndarray] = {}
    for record in records:
        source_path = record["source_path"]
        u, v, profile = _read_vector(source_path)
        speed = speed_array(u, v)
        frame_key = f"{record['plan_name']}/{record['job_id']}/{record['time']}"
        output_file = output_path / "speed" / record["plan_name"] / record["job_id"] / (
            f"{source_path.stem}_{record['time'].replace(':', '').replace('-', '')[:15]}_speed.tif"
        )
        _atomic_write_raster(
            output_file,
            speed,
            profile,
            {
                "band_name": "speed",
                "product_type": "speed",
                "source_file": str(source_path),
                "source_time": record["time"],
                "analytics_version": ANALYTICS_VERSION,
                "config_hash": config_hash_value,
                "units": "m s-1",
                "nodata": "-9999",
                "method": "hypot(uo,vo)",
            },
        )
        speed_records.append(FrameRecord(record["plan_name"], record["job_id"], record["time"], source_path, output_file))
        speed_arrays[frame_key] = speed
        profiles[frame_key] = profile
        stats = frame_statistics(speed * 0 + u, speed * 0 + v, ddof=ddof, percentile_method=percentile_method)
        area_key = (speed.shape[0], speed.shape[1], str(profile["transform"]))
        area = area_cache.setdefault(area_key, _cell_area_m2(profile["transform"], speed.shape[0], speed.shape[1]))
        static_expected_masks.setdefault(record["plan_name"], np.isfinite(u) & np.isfinite(v))
        spatial = _spatial_mean_vector(
            u,
            v,
            area,
            MINIMUM_VALID_AREA_FRACTION,
            static_expected_masks[record["plan_name"]],
        )
        spatial["time"] = record["time"]
        spatial["job_id"] = record["job_id"]
        spatial_by_plan.setdefault(record["plan_name"], []).append(spatial)
        stats["valid_area_m2"] = float(area[np.isfinite(speed)].sum())
        stats["valid_area_fraction"] = spatial["valid_area_fraction"]
        stats["spatial_timestep_accepted"] = spatial["accepted"]
        stats["spatial_mean_u"] = spatial["mean_u"]
        stats["spatial_mean_v"] = spatial["mean_v"]
        stats["spatial_resultant_speed"] = spatial["resultant_speed"]
        stats["spatial_resultant_direction"] = spatial["resultant_direction"]
        stats.update(
            {
                "plan_name": record["plan_name"],
                "job_id": record["job_id"],
                "time": record["time"],
                "speed_product": str(output_file),
                "speed_product_sha256": sha256_file(output_file),
                "aoi_id": study_area.get("aoi_id"),
                "aoi_geometry_status": study_area.get("exact_polygon_status"),
                "valid_area_fraction_rule": MINIMUM_VALID_AREA_FRACTION,
            }
        )
        rows.append(stats)
        products.append(
            {
                "product_type": "speed",
                "path": str(output_file),
                "sha256": sha256_file(output_file),
                "plan_name": record["plan_name"],
                "job_id": record["job_id"],
                "time": record["time"],
                "source_path": str(source_path),
                "units": "m s-1",
                "config_hash": config_hash_value,
                "analytics_version": ANALYTICS_VERSION,
            }
        )

    monthly_records = [record for record in speed_records if record.plan_name == "monthly_all"]
    daily_records = [record for record in speed_records if record.plan_name == "daily_jfm"]
    monthly_climatologies: dict[int, np.ndarray] = {}
    for month in range(1, 13):
        group = [record.speed_path for record in monthly_records if int(record.time[5:7]) == month]
        monthly_climatologies[month] = _mean_rasters(group)
        sample = next(record for record in monthly_records if int(record.time[5:7]) == month)
        output_file = output_path / "climatology" / f"monthly_speed_{month:02d}.tif"
        _atomic_write_raster(output_file, monthly_climatologies[month], profiles[f"monthly_all/{sample.job_id}/{sample.time}"], {
            "band_name": "monthly_speed_climatology",
            "product_type": "monthly_climatology_speed",
            "month": str(month),
            "reference_period": "2015-2025",
            "weighting": "equal_monthly_frames",
            "analytics_version": ANALYTICS_VERSION,
            "config_hash": config_hash_value,
            "units": "m s-1",
        })
        products.append({"product_type": "monthly_climatology_speed", "path": str(output_file), "sha256": sha256_file(output_file), "month": month, "reference_period": "2015-2025"})

    jfm_climatology = _mean_rasters([record.speed_path for record in daily_records])
    jfm_sample = daily_records[0]
    jfm_file = output_path / "climatology" / "jfm_speed.tif"
    _atomic_write_raster(jfm_file, jfm_climatology, profiles[f"daily_jfm/{jfm_sample.job_id}/{jfm_sample.time}"], {
        "band_name": "jfm_speed_climatology",
        "product_type": "jfm_climatology_speed",
        "reference_period": "2015-2025",
        "weighting": "equal_daily_frames",
        "analytics_version": ANALYTICS_VERSION,
        "config_hash": config_hash_value,
        "units": "m s-1",
    })
    products.append({"product_type": "jfm_climatology_speed", "path": str(jfm_file), "sha256": sha256_file(jfm_file), "reference_period": "2015-2025"})

    anomaly_products = 0
    for record in speed_records:
        month = int(record.time[5:7])
        baseline = monthly_climatologies[month] if record.plan_name == "monthly_all" else jfm_climatology
        values = speed_arrays[f"{record.plan_name}/{record.job_id}/{record.time}"]
        output_file = output_path / "anomaly" / record.plan_name / record.job_id / (
            f"{record.source_path.stem}_{record.time.replace(':', '').replace('-', '')[:15]}_speed_anomaly.tif"
        )
        _atomic_write_raster(output_file, values - baseline, profiles[f"{record.plan_name}/{record.job_id}/{record.time}"], {
            "band_name": "speed_anomaly",
            "product_type": "speed_anomaly",
            "reference_period": "2015-2025",
            "baseline": "monthly_climatology" if record.plan_name == "monthly_all" else "jfm_climatology",
            "source_time": record.time,
            "analytics_version": ANALYTICS_VERSION,
            "config_hash": config_hash_value,
            "units": "m s-1",
        })
        products.append({"product_type": "speed_anomaly", "path": str(output_file), "sha256": sha256_file(output_file), "plan_name": record.plan_name, "job_id": record.job_id, "time": record.time})
        anomaly_products += 1

    annual_arrays: list[np.ndarray] = []
    years = list(range(2015, 2026))
    for year in years:
        group = [record.speed_path for record in monthly_records if int(record.time[:4]) == year]
        annual_arrays.append(_mean_rasters(group))
    trend = _linear_slope(years, annual_arrays)
    trend_sample = monthly_records[0]
    trend_file = output_path / "trend" / "monthly_annual_mean_speed_slope.tif"
    _atomic_write_raster(trend_file, trend, profiles[f"monthly_all/{trend_sample.job_id}/{trend_sample.time}"], {
        "band_name": "speed_trend_slope",
        "product_type": "exploratory_trend_slope",
        "reference_period": "2015-2025",
        "method": "ordinary_least_squares_per_pixel",
        "interpretation": "exploratory; no inferential claim",
        "analytics_version": ANALYTICS_VERSION,
        "config_hash": config_hash_value,
        "units": "m s-1 year-1",
    })
    products.append({"product_type": "exploratory_trend_slope", "path": str(trend_file), "sha256": sha256_file(trend_file), "reference_period": "2015-2025", "units": "m s-1 year-1"})

    threshold_rows: list[dict[str, Any]] = []
    current_rose_rows: list[dict[str, Any]] = []
    current_rose_summaries: list[dict[str, Any]] = []
    current_rose_figures: list[dict[str, Any]] = []
    for plan_name in ("daily_jfm", "monthly_all"):
        series = spatial_by_plan.get(plan_name, [])
        valid_series = [item for item in series if item["accepted"]]
        if not valid_series:
            raise AnalyticsError(f"no valid spatial timesteps remain for {plan_name}")
        speeds = [float(item["resultant_speed"]) for item in valid_series]
        threshold = _quantile(speeds, 0.90, percentile_method)
        expected_count = len(series)
        valid_count = len(valid_series)
        missing_count = expected_count - valid_count
        period_start = min(str(item["time"]) for item in series)[:10]
        period_end = max(str(item["time"]) for item in series)[:10]
        source = source_metadata.get(plan_name, {})
        dataset_id = source.get("dataset_id") or (
            "cmems_mod_glo_phy_my_0.083deg_P1D-m" if plan_name == "daily_jfm" else "cmems_mod_glo_phy_my_0.083deg_P1M-m"
        )
        dataset_version = source.get("dataset_version", "202311")
        common = {
            "analysis_plan_id": plan_name,
            "unit_id": study_area.get("aoi_id"),
            "unit_type": "aoi",
            "period_start": period_start,
            "period_end": period_end,
            "time_resolution": "daily" if plan_name == "daily_jfm" else "monthly",
            "depth_m": depth_config.get("analysis_depth_m"),
            "dataset_id": dataset_id,
            "dataset_version": dataset_version,
            "config_hash": config_hash_value,
        }
        threshold_row = {
            **common,
            "threshold_method": "relative_high_current_threshold_global_p90",
            "threshold_label": "Ambang kondisi arus relatif tinggi, P90",
            "threshold_global_p90_mps": threshold,
            "local_p90_mps": threshold,
            "valid_count": valid_count,
            "missing_count": missing_count,
            "expected_count": expected_count,
            "valid_percentage": 100.0 * valid_count / expected_count,
            "exceedance_count": int(sum(value > threshold for value in speeds)),
            "non_exceedance_count": int(sum(value <= threshold for value in speeds)),
            "exceedance_percentage": 100.0 * sum(value > threshold for value in speeds) / valid_count,
            "comparison_operator": ">",
            "minimum_valid_area_fraction": MINIMUM_VALID_AREA_FRACTION,
            "aoi_geometry_status": study_area.get("exact_polygon_status"),
        }
        threshold_rows.append(threshold_row)
        bin_definitions = _speed_bin_definitions(speeds, threshold, percentile_method)
        counts: dict[tuple[str, str], int] = {}
        sector_counts: dict[str, int] = {label: 0 for label in SECTOR_LABELS}
        bin_counts: dict[str, int] = {str(item["speed_bin"]): 0 for item in bin_definitions}
        zero_count = 0
        for item in valid_series:
            speed_value = float(item["resultant_speed"])
            speed_bin = _speed_bin_for_value(speed_value, bin_definitions)
            bin_counts[speed_bin] += 1
            if speed_bin == "ZERO":
                zero_count += 1
                continue
            bearing = float(item["resultant_direction"])
            sector_index = int(math.floor(((bearing + 11.25) % 360.0) / 22.5))
            sector = SECTOR_LABELS[sector_index]
            sector_counts[sector] += 1
            counts[(sector, speed_bin)] = counts.get((sector, speed_bin), 0) + 1
        for sector_index, sector in enumerate(SECTOR_LABELS):
            lower = (sector_index * 22.5 - 11.25) % 360.0
            upper = (sector_index * 22.5 + 11.25) % 360.0
            for item in bin_definitions:
                speed_bin = str(item["speed_bin"])
                count = counts.get((sector, speed_bin), 0)
                current_rose_rows.append({
                    **common,
                    "direction_sector": sector,
                    "direction_center_deg": sector_index * 22.5,
                    "direction_lower_deg": lower,
                    "direction_upper_deg": upper,
                    "speed_bin": speed_bin,
                    "speed_lower_mps": item["lower"],
                    "speed_upper_mps": item["upper"],
                    "count": count,
                    "frequency_percentage": 100.0 * count / valid_count,
                    "valid_count": valid_count,
                    "zero_count": zero_count,
                    "missing_count": missing_count,
                    "sparse_class": count < int(rose_config.get("sparse_class_count", 5)),
                    "threshold_global_p90_mps": threshold,
                    "direction_convention": "towards",
                })
        current_rose_rows.append({
            **common,
            "direction_sector": "UNDEFINED",
            "direction_center_deg": None,
            "direction_lower_deg": None,
            "direction_upper_deg": None,
            "speed_bin": "ZERO",
            "speed_lower_mps": None,
            "speed_upper_mps": ZERO_EPSILON_MPS,
            "count": zero_count,
            "frequency_percentage": 100.0 * zero_count / valid_count,
            "valid_count": valid_count,
            "zero_count": zero_count,
            "missing_count": missing_count,
            "sparse_class": zero_count < int(rose_config.get("sparse_class_count", 5)),
            "threshold_global_p90_mps": threshold,
            "direction_convention": "towards",
        })
        mean_u = float(np.mean([float(item["mean_u"]) for item in valid_series]))
        mean_v = float(np.mean([float(item["mean_v"]) for item in valid_series]))
        mean_speed = float(np.mean(speeds))
        resultant_speed = float(np.hypot(mean_u, mean_v))
        summary = {
            **common,
            "resultant_direction_deg": resultant_direction_degrees(mean_u, mean_v),
            "resultant_speed_mps": resultant_speed,
            "mean_speed_mps": mean_speed,
            "persistence": None if mean_speed == 0 else resultant_speed / mean_speed,
            "dominant_sector": max(sector_counts, key=sector_counts.get) if sum(sector_counts.values()) else None,
            "dominant_speed_bin": max(bin_counts, key=bin_counts.get),
            "valid_count": valid_count,
            "zero_count": zero_count,
            "missing_count": missing_count,
            "valid_percentage": 100.0 * valid_count / expected_count,
            "zero_percentage": 100.0 * zero_count / valid_count,
            "missing_percentage": 100.0 * missing_count / expected_count,
            "threshold_global_p90_mps": threshold,
            "direction_convention": "towards",
            "direction_reference": "true_north",
            "direction_rotation": "clockwise",
            "sector_count": 16,
            "sector_width_deg": 22.5,
            "zero_epsilon_mps": ZERO_EPSILON_MPS,
            "speed_bin_method": "global_aoi_quantiles",
            "speed_bin_quantiles": [0.25, 0.50, 0.75, 0.90],
            "speed_bin_definitions": bin_definitions,
            "direction_caveat": "Resultant direction can be misleading when opposing vectors cancel; inspect persistence and sector frequencies.",
            "aoi_geometry_status": study_area.get("exact_polygon_status"),
        }
        current_rose_summaries.append(summary)
        figure_file = output_path / "figures" / f"current_rose_{plan_name}.svg"
        _write_current_rose_svg(figure_file, [row for row in current_rose_rows if row["analysis_plan_id"] == plan_name], summary, bin_definitions)
        current_rose_figures.append({"path": str(figure_file), "sha256": sha256_file(figure_file), "analysis_plan_id": plan_name, "format": "svg"})

    threshold_file = output_path / "tables" / "threshold_exceedance.csv"
    threshold_fields = [
        "analysis_plan_id", "unit_id", "unit_type", "threshold_method", "threshold_label", "threshold_global_p90_mps", "local_p90_mps",
        "valid_count", "missing_count", "expected_count", "valid_percentage", "exceedance_count", "non_exceedance_count", "exceedance_percentage",
        "comparison_operator", "period_start", "period_end", "time_resolution", "depth_m", "dataset_id", "dataset_version", "config_hash", "minimum_valid_area_fraction", "aoi_geometry_status",
    ]
    _write_csv(threshold_file, threshold_rows, threshold_fields)
    rose_long_file = output_path / "tables" / "current_rose_long.csv"
    rose_long_fields = [
        "analysis_plan_id", "unit_id", "unit_type", "direction_sector", "direction_center_deg", "direction_lower_deg", "direction_upper_deg",
        "speed_bin", "speed_lower_mps", "speed_upper_mps", "count", "frequency_percentage", "valid_count", "zero_count", "missing_count",
        "sparse_class", "threshold_global_p90_mps", "period_start", "period_end", "time_resolution", "depth_m", "direction_convention", "dataset_id", "config_hash",
    ]
    _write_csv(rose_long_file, current_rose_rows, rose_long_fields)
    rose_summary_file = output_path / "tables" / "current_rose_summary.csv"
    rose_summary_fields = [
        "analysis_plan_id", "unit_id", "unit_type", "resultant_direction_deg", "resultant_speed_mps", "mean_speed_mps", "persistence",
        "dominant_sector", "dominant_speed_bin", "valid_count", "zero_count", "missing_count", "valid_percentage", "zero_percentage", "missing_percentage",
        "threshold_global_p90_mps", "period_start", "period_end", "time_resolution", "depth_m", "direction_convention", "direction_reference", "direction_rotation",
        "sector_count", "sector_width_deg", "zero_epsilon_mps", "speed_bin_method", "speed_bin_quantiles", "direction_caveat", "aoi_geometry_status", "dataset_id", "config_hash",
    ]
    summary_csv_rows = [dict(row, speed_bin_quantiles=json.dumps(row["speed_bin_quantiles"]), speed_bin_definitions=json.dumps(row["speed_bin_definitions"])) for row in current_rose_summaries]
    _write_csv(rose_summary_file, summary_csv_rows, rose_summary_fields)

    table_file = output_path / "tables" / "timestep_speed_statistics.csv"
    table_file.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=table_file.parent, prefix=f".{table_file.name}.", suffix=".tmp", delete=False) as handle:
        temporary_table = Path(handle.name)
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_table, table_file)

    table_records = [
        {"path": str(table_file), "sha256": sha256_file(table_file), "row_count": len(rows)},
        {"path": str(threshold_file), "sha256": sha256_file(threshold_file), "row_count": len(threshold_rows)},
        {"path": str(rose_long_file), "sha256": sha256_file(rose_long_file), "row_count": len(current_rose_rows)},
        {"path": str(rose_summary_file), "sha256": sha256_file(rose_summary_file), "row_count": len(current_rose_summaries)},
    ]
    analytics_manifest = {
        "status": "PASS_WITH_NOTES",
        "stage": "T5-025/T5-026",
        "analytics_version": ANALYTICS_VERSION,
        "source_conversion_manifest": str(conversion_path),
        "source_conversion_manifest_sha256": sha256_file(conversion_path),
        "config_hash": config_hash_value,
        "method": {
            "ddof": ddof,
            "percentile_method": percentile_method,
            "direction_convention": DIRECTION_CONVENTION,
            "threshold_method": "relative_high_current_threshold_global_p90",
            "threshold_scope": "global_aoi_per_analysis_plan_id",
            "comparison_operator": ">",
            "minimum_valid_area_fraction": MINIMUM_VALID_AREA_FRACTION,
            "current_rose": {
                "rose_type": "area_weighted_mean_vector_time_series",
                "direction_convention": "towards",
                "direction_reference": "true_north",
                "direction_rotation": "clockwise",
                "sector_count": 16,
                "sector_width_deg": 22.5,
                "zero_epsilon_mps": ZERO_EPSILON_MPS,
                "speed_bin_method": "global_aoi_quantiles",
                "speed_bin_quantiles": [0.25, 0.50, 0.75, 0.90],
                "missing_policy": "pairwise_valid_uv_and_minimum_valid_area",
                "minimum_valid_area_fraction": MINIMUM_VALID_AREA_FRACTION,
            },
        },
        "analysis_period": analysis_period,
        "aoi": study_area,
        "statistics_config": statistics_config,
        "frame_count": len(rows),
        "products": products,
        "tables": table_records,
        "figures": current_rose_figures,
        "decisions": {"OD-004": "RESOLVED", "OD-005": "RESOLVED", "OD-006": "RESOLVED"},
        "zone_status": "NOT_AVAILABLE_NO_ZONE_GEOMETRIES",
        "limitations": [
            "T5-023 trend is exploratory and does not establish causality or statistical significance.",
            "Zonal area is an approximate EPSG:4326 bbox area; exact water polygon is pending.",
            "T5-017 and T5-019 are calculated for the AOI. Zone outputs require user-supplied zone IDs and valid geometries.",
            "The static expected-ocean mask is the baseline valid-pair mask from the validated collection because an exact water polygon was not supplied; valid-area QC detects additional timestep loss against that mask.",
            "Current rose is a research summary and not a safety, operational, or hazard indicator.",
        ],
    }
    _atomic_write_json(Path(report_path), analytics_manifest)
    return analytics_manifest


def audit_analytics_manifest(manifest_path: str | Path) -> dict[str, Any]:
    """Audit every derived product checksum, raster schema, figure, and table."""

    manifest_path_resolved = Path(manifest_path).resolve()
    manifest = _safe_json(manifest_path_resolved)
    products = manifest.get("products")
    if not isinstance(products, list) or not products:
        raise AnalyticsError("analytics manifest has no products")
    checked_rasters = 0
    checked_tables = 0
    checked_figures = 0
    for product in products:
        if not isinstance(product, dict):
            raise AnalyticsError("analytics product record is invalid")
        path = Path(str(product.get("path", ""))).resolve()
        if not path.is_file():
            raise AnalyticsError(f"analytics product is missing: {path}")
        if sha256_file(path) != str(product.get("sha256", "")):
            raise AnalyticsError(f"analytics product checksum mismatch: {path}")
        if path.suffix.lower() == ".tif":
            with rasterio.open(path) as source:
                if source.count != 1 or source.dtypes != ("float32",):
                    raise AnalyticsError(f"analytics raster schema mismatch: {path}")
                if source.nodata != -9999.0 or source.crs is None or source.crs.to_string() != "EPSG:4326":
                    raise AnalyticsError(f"analytics raster spatial metadata mismatch: {path}")
                tags = source.tags()
                if tags.get("analytics_version") != manifest.get("analytics_version"):
                    raise AnalyticsError(f"analytics version tag mismatch: {path}")
                if tags.get("config_hash") != manifest.get("config_hash"):
                    raise AnalyticsError(f"analytics config tag mismatch: {path}")
            checked_rasters += 1
        else:
            raise AnalyticsError(f"unsupported analytics product extension: {path}")
    for table in manifest.get("tables", []):
        if not isinstance(table, dict):
            raise AnalyticsError("analytics table record is invalid")
        path = Path(str(table.get("path", ""))).resolve()
        if not path.is_file() or sha256_file(path) != str(table.get("sha256", "")):
            raise AnalyticsError(f"analytics table checksum or path mismatch: {path}")
        with path.open(encoding="utf-8", newline="") as handle:
            row_count = sum(1 for _ in csv.DictReader(handle))
        if row_count != int(table.get("row_count", -1)):
            raise AnalyticsError(f"analytics table row count mismatch: {path}")
        checked_tables += 1
    for figure in manifest.get("figures", []):
        if not isinstance(figure, dict):
            raise AnalyticsError("analytics figure record is invalid")
        path = Path(str(figure.get("path", ""))).resolve()
        if not path.is_file() or sha256_file(path) != str(figure.get("sha256", "")):
            raise AnalyticsError(f"analytics figure checksum or path mismatch: {path}")
        if path.suffix.lower() != ".svg" or "<svg" not in path.read_text(encoding="utf-8"):
            raise AnalyticsError(f"analytics figure is not a valid SVG: {path}")
        checked_figures += 1
    return {
        "status": "PASS_WITH_NOTES",
        "analytics_version": manifest.get("analytics_version"),
        "product_count": len(products),
        "checked_raster_count": checked_rasters,
        "checked_table_count": checked_tables,
        "checked_figure_count": checked_figures,
        "frame_count": manifest.get("frame_count"),
        "limitations": manifest.get("limitations", []),
    }


__all__ = [
    "ANALYTICS_VERSION",
    "AnalyticsError",
    "SECTOR_LABELS",
    "audit_analytics_manifest",
    "direction_sector_array",
    "frame_statistics",
    "mean_components_array",
    "resultant_direction_degrees",
    "run_collection_analytics",
    "speed_array",
]
