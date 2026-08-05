"""Strict, offline loader for the M1 configuration baseline.

This module only reads local JSON files. It never initializes Earth Engine,
contacts Copernicus, starts a task, or writes an asset.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .constants import (
    ANALYSIS_DEPTH_M,
    DAILY_DATASET_ID,
    DIRECTION_CONVENTION,
    DEPTH_TOLERANCE_M,
    DISPLAY_TIMEZONE,
    JFM_DAILY_COUNT,
    MONTHLY_COUNT,
    MONTHLY_DATASET_ID,
    PRODUCT_ID,
    PROJECT_PERIOD_END_EXCLUSIVE,
    PROJECT_PERIOD_START,
    SPEED_STATISTIC_NAMES,
    VECTOR_STATISTIC_NAMES,
)


class ConfigError(ValueError):
    """Raised when a configuration is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class StudyArea:
    aoi_id: str
    crs: str
    west: float
    east: float
    south: float
    north: float


@dataclass(frozen=True)
class ProjectConfig:
    project_id: str
    asset_root: str


@dataclass(frozen=True)
class M1Config:
    study_area: StudyArea
    project: ProjectConfig
    period: dict[str, Any]
    depth: dict[str, Any]
    statistics: dict[str, Any]
    asset_naming: dict[str, Any]


def _read_json(root: Path, name: str) -> dict[str, Any]:
    path = root / name
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"missing configuration: {name}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON: {name}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"configuration must be an object: {name}")
    return data


def _project_from(data: dict[str, Any]) -> ProjectConfig:
    project_id = data.get("earth_engine_project_id")
    asset_root = data.get("earth_engine_asset_root")
    if not isinstance(project_id, str) or not project_id:
        raise ConfigError("earth_engine_project_id is required")
    if not isinstance(asset_root, str) or not asset_root:
        raise ConfigError("earth_engine_asset_root is required")
    expected_prefix = f"projects/{project_id}/assets/"
    if not asset_root.startswith(expected_prefix):
        raise ConfigError("asset root does not belong to configured project")
    return ProjectConfig(project_id=project_id, asset_root=asset_root)


def _study_area_from(data: dict[str, Any]) -> StudyArea:
    try:
        area = StudyArea(
            aoi_id=str(data["aoi_id"]),
            crs=str(data["crs"]),
            west=float(data["west"]),
            east=float(data["east"]),
            south=float(data["south"]),
            north=float(data["north"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError("study area is incomplete") from exc
    if area.crs != "EPSG:4326":
        raise ConfigError("study area must use EPSG:4326")
    if not (-180 <= area.west < area.east <= 180):
        raise ConfigError("study area requires west < east within longitude bounds")
    if not (-90 <= area.south < area.north <= 90):
        raise ConfigError("study area requires south < north within latitude bounds")
    return area


def load_m1_config(config_root: str | Path) -> M1Config:
    """Load and validate the offline M1 configuration set."""

    root = Path(config_root)
    study = _read_json(root, "study_area.json")
    period = _read_json(root, "analysis_period.json")
    depth = _read_json(root, "depth_selection.json")
    statistics = _read_json(root, "statistics.json")
    asset_naming = _read_json(root, "asset_naming.json")
    local = _read_json(root, "local.example.json")
    project = _project_from(local)
    area = _study_area_from(study)

    if period.get("full_period", {}).get("start") != PROJECT_PERIOD_START:
        raise ConfigError("project period start does not match approved baseline")
    if period.get("full_period", {}).get("end_exclusive") != PROJECT_PERIOD_END_EXCLUSIVE:
        raise ConfigError("project period end does not match approved baseline")
    if period.get("monthly_count_expected") != MONTHLY_COUNT:
        raise ConfigError("monthly count does not match approved baseline")
    if period.get("daily_jfm_count_expected") != JFM_DAILY_COUNT:
        raise ConfigError("daily JFM count does not match approved baseline")
    if period.get("years") != list(range(2015, 2026)):
        raise ConfigError("period years do not match approved baseline")
    if period.get("january_march") != {
        "start_month": 1,
        "start_day": 1,
        "end_month_exclusive": 4,
        "end_day": 1,
    }:
        raise ConfigError("January-March period definition does not match approved baseline")

    depth_value = float(depth.get("analysis_depth_m", -1))
    if abs(depth_value - ANALYSIS_DEPTH_M) > DEPTH_TOLERANCE_M:
        raise ConfigError("analysis depth does not match approved baseline")
    if depth.get("label") != "top_model_layer":
        raise ConfigError("depth label does not match approved baseline")
    if depth.get("selection_method") != "exact_after_verification":
        raise ConfigError("depth selection method does not match approved baseline")
    if abs(float(depth.get("tolerance_m", -1)) - DEPTH_TOLERANCE_M) > 1e-12:
        raise ConfigError("depth tolerance does not match approved baseline")
    if depth.get("full_50_level_extraction_status") != "VERIFIED_USER_ACTIVE_DESCRIBE":
        raise ConfigError("full depth extraction status must be verified explicitly")
    if statistics.get("speed_statistics") != list(SPEED_STATISTIC_NAMES):
        raise ConfigError("speed statistic names do not match approved baseline")
    if statistics.get("vector_statistics") != list(VECTOR_STATISTIC_NAMES):
        raise ConfigError("vector statistic names do not match approved baseline")
    if statistics.get("direction_convention") != DIRECTION_CONVENTION:
        raise ConfigError("direction convention does not match approved baseline")
    if statistics.get("speed_thresholds_mps") != []:
        raise ConfigError("speed thresholds must remain empty; T5-017 uses derived P90")
    if statistics.get("threshold_method") != "relative_high_current_threshold_global_p90":
        raise ConfigError("threshold method must be the approved global AOI P90")
    if statistics.get("minimum_valid_area_fraction") != 0.95:
        raise ConfigError("minimum valid area fraction must be 0.95")
    if statistics.get("threshold_status") != "RESOLVED_GLOBAL_AOI_P90":
        raise ConfigError("threshold status must record the resolved P90 decision")
    rose = statistics.get("current_rose")
    if not isinstance(rose, dict) or rose.get("sector_count") != 16:
        raise ConfigError("current rose must use 16 sectors")
    if rose.get("zero_epsilon_mps") != 1e-6:
        raise ConfigError("current rose zero epsilon must be 1e-6 m s-1")
    if local.get("copernicus_product_id") != PRODUCT_ID:
        raise ConfigError("Copernicus product ID does not match approved baseline")
    if local.get("copernicus_daily_dataset_id") != DAILY_DATASET_ID:
        raise ConfigError("daily dataset ID does not match approved baseline")
    if local.get("copernicus_monthly_dataset_id") != MONTHLY_DATASET_ID:
        raise ConfigError("monthly dataset ID does not match approved baseline")
    if local.get("display_timezone") != DISPLAY_TIMEZONE:
        raise ConfigError("display timezone does not match approved baseline")
    if asset_naming.get("earth_engine_project_id") != project.project_id:
        raise ConfigError("asset naming project does not match local project")
    if asset_naming.get("earth_engine_asset_root") != project.asset_root:
        raise ConfigError("asset naming root does not match local asset root")

    return M1Config(
        study_area=area,
        project=project,
        period=period,
        depth=depth,
        statistics=statistics,
        asset_naming=asset_naming,
    )
