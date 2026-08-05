from __future__ import annotations

from datetime import date, timedelta
from dataclasses import replace
from pathlib import Path
import runpy
import tempfile
import unittest

import numpy as np
import xarray as xr


ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / "python" / "07_validate_stage4.py"))


def _write_fixture(
    folder: Path,
    *,
    plan_name: str = "daily_jfm",
    year: int = 2020,
    month: int = 2,
    include_vo: bool = True,
    unit: str = "m s-1",
    depth: float = 0.494025,
    missing_day: int | None = None,
    duplicate_timestamp: bool = False,
    encoded: bool = False,
    all_nan: bool = False,
    sentinel: bool = False,
    outlier: bool = False,
    descending_latitude: bool = False,
    broken_latitude: bool = False,
    vo_mask_mismatch: bool = False,
) -> tuple[Path, dict[str, object]]:
    start = date(year, month, 1)
    count = 1 if plan_name == "monthly_all" else (date(year, month + 1, 1) - start).days if month < 12 else 31
    times = [start + timedelta(days=index) for index in range(count)]
    if missing_day is not None:
        times.remove(date(year, month, missing_day))
    if duplicate_timestamp:
        times[-1] = times[-2]
    time_values = np.array(times, dtype="datetime64[ns]")
    if broken_latitude:
        latitudes = np.array([0.0, 1.0, 0.0], dtype="float32")
    elif descending_latitude:
        latitudes = np.array([0.0, -1.0], dtype="float32")
    else:
        latitudes = np.array([-1.0, 0.0], dtype="float32")
    coords = {
        "time": time_values,
        "depth": np.array([depth], dtype="float32"),
        "latitude": latitudes,
        "longitude": np.array([130.0, 131.0], dtype="float32"),
    }
    shape = (len(times), 1, len(latitudes), 2)
    values = np.zeros(shape, dtype="float32")
    values[..., 0, 1] = 1.0
    if encoded:
        values[..., 0, 0] = 0.0
        values[..., 0, 1] = 1.0
        values[..., 1 if len(latitudes) > 1 else 0, 0] = np.nan
        values[..., 1 if len(latitudes) > 1 else 0, 1] = 2.0
        if all_nan:
            values[:] = np.nan
        if outlier:
            values[..., 0, 0] = 20.0
    elif sentinel:
        values[..., 0, 0] = -32767.0
    data = {"uo": (("time", "depth", "latitude", "longitude"), values, {"units": unit})}
    if include_vo:
        vo_values = values.copy()
        if vo_mask_mismatch:
            vo_values[..., 0, 0] = np.nan
        data["vo"] = (("time", "depth", "latitude", "longitude"), vo_values, {"units": unit})
    dataset = xr.Dataset(data, coords=coords)
    dataset["time"].encoding["calendar"] = "standard"
    if encoded:
        for name in ("uo", "vo") if include_vo else ("uo",):
            dataset[name].attrs["valid_min"] = -10
            dataset[name].attrs["valid_max"] = 10
            dataset[name].encoding.update(
                {"_FillValue": -32767, "scale_factor": 0.5, "add_offset": 0.0, "dtype": "int16"}
            )
    path = folder / "fixture.nc"
    dataset.to_netcdf(path, engine="h5netcdf")
    row = {
        "job_id": "daily_jfm_2020_02" if plan_name == "daily_jfm" else "monthly_2020_02",
        "plan_name": plan_name,
        "year": year,
        "month": month,
        "status": "ready_for_stage4",
        "checksum": "a" * 64,
        "output_directory": ".",
        "output_filename": path.name,
        "dataset_id": "fixture-dataset",
        "dataset_version": "fixture-version",
        "dataset_part": "fixture-part",
        "start_datetime": f"{year:04d}-{month:02d}-01T00:00:00",
        "end_datetime": f"{year:04d}-{month:02d}-28T23:59:59",
    }
    return path, row


class Stage4ValidationTests(unittest.TestCase):
    def _validate(self, **kwargs: object):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path, row = _write_fixture(Path(folder.name), **kwargs)
        return MODULE["_validate_dataset"](
            path, row, target_depth_m=0.494025, depth_tolerance_m=1e-6
        )

    def _validate_wp2(self, **kwargs: object):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path, row = _write_fixture(Path(folder.name), encoded=True, **kwargs)
        return MODULE["_validate_dataset"](
            path, row, target_depth_m=0.494025, depth_tolerance_m=1e-6, scope="wp2"
        )

    def _validate_full(self, **kwargs: object):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path, row = _write_fixture(Path(folder.name), encoded=True, **kwargs)
        return MODULE["_validate_dataset"](
            path, row, target_depth_m=0.494025, depth_tolerance_m=1e-6, scope="full"
        )

    def test_nominal_daily_fixture_passes(self) -> None:
        result = self._validate()
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.time_count, 29)

    def test_missing_vo_fails(self) -> None:
        result = self._validate(include_vo=False)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("missing variables" in error for error in result.errors))

    def test_bad_unit_fails_without_conversion(self) -> None:
        result = self._validate(unit="knots")
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("unsupported units" in error for error in result.errors))

    def test_bad_depth_fails(self) -> None:
        result = self._validate(depth=1.0)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("depth mismatch" in error for error in result.errors))

    def test_missing_timestep_fails(self) -> None:
        result = self._validate(missing_day=15)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("timestamp sequence mismatch" in error for error in result.errors))

    def test_duplicate_timestamp_fails(self) -> None:
        result = self._validate(duplicate_timestamp=True)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("duplicate timestamps" in error for error in result.errors))

    def test_leap_year_case_passes(self) -> None:
        result = self._validate(year=2024)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.time_count, 29)

    def test_monthly_plan_has_one_first_of_month_timestamp(self) -> None:
        result = self._validate(plan_name="monthly_all", year=2025, month=2)
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.time_count, 1)
        self.assertEqual(result.time_first, "2025-02-01T00:00:00.000000000")

    def test_wp2_nominal_mask_fill_encoding_and_plausibility_pass(self) -> None:
        result = self._validate_wp2()
        self.assertEqual(result.status, "PASS")
        self.assertTrue(any("T4-005" in check for check in result.checks))
        self.assertTrue(any("scale_factor=0.5" in detail for detail in result.details))

    def test_wp2_valid_zero_is_not_masked(self) -> None:
        result = self._validate_wp2()
        self.assertEqual(result.status, "PASS")
        self.assertTrue(any("raw_fill_count=" in detail for detail in result.details))

    def test_wp2_descending_latitude_passes(self) -> None:
        result = self._validate_wp2(descending_latitude=True)
        self.assertEqual(result.status, "PASS")
        self.assertTrue(any("latitude_order=descending" in detail for detail in result.details))

    def test_wp2_broken_latitude_fails(self) -> None:
        result = self._validate_wp2(broken_latitude=True)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("not strictly monotonic" in error for error in result.errors))

    def test_wp2_all_nan_fails(self) -> None:
        result = self._validate_wp2(all_nan=True)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("no finite decoded values" in error for error in result.errors))

    def test_wp2_sentinel_fails(self) -> None:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path, row = _write_fixture(Path(folder.name), sentinel=True)
        result = MODULE["_validate_dataset"](
            path, row, target_depth_m=0.494025, depth_tolerance_m=1e-6, scope="wp2"
        )
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("sentinel" in error for error in result.errors))

    def test_wp2_outlier_exceeding_encoded_range_fails(self) -> None:
        result = self._validate_wp2(outlier=True)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("exceed encoded valid range" in error for error in result.errors))

    def test_full_quality_metrics_pass_and_are_recorded(self) -> None:
        result = self._validate_full()
        self.assertEqual(result.status, "PASS")
        self.assertEqual([metric[0] for metric in result.coverage_metrics], ["uo", "vo"])
        self.assertEqual([metric[0] for metric in result.distribution_metrics], ["uo", "vo"])
        self.assertTrue(any("uo_vo_mask_equal=true" in value for value in result.consistency))
        self.assertTrue(any("T4-009" in check for check in result.checks))
        self.assertTrue(any("T4-010" in check for check in result.checks))
        self.assertTrue(any("T4-011" in check for check in result.checks))

    def test_full_uo_vo_mask_mismatch_fails(self) -> None:
        result = self._validate_full(vo_mask_mismatch=True)
        self.assertEqual(result.status, "FAIL")
        self.assertTrue(any("masks are not identical" in error for error in result.errors))

    def test_full_manifest_contains_quality_and_provenance(self) -> None:
        result = self._validate_full()
        report = MODULE["Stage4ValidationReport"](
            (result,), 0.494025, 1e-6, "fixture-config", 1, "fixture", "full"
        )
        manifest = MODULE["build_manifest"](report)
        entry = manifest["entries"][0]
        self.assertEqual(manifest["scope"], "FULL")
        self.assertEqual(entry["dataset_version"], "fixture-version")
        self.assertEqual(entry["coverage"][0]["variable"], "uo")
        self.assertEqual(entry["consistency"][0], "uo_vo_mask_equal=true")
        self.assertTrue(manifest["period_distributions"])

    def test_full_report_and_gate_include_stage4_counts(self) -> None:
        result = self._validate_full()
        report = MODULE["Stage4ValidationReport"](
            (result,), 0.494025, 1e-6, "fixture-config", 1, "fixture", "full"
        )
        rendered_report = MODULE["render_validation_report"](report)
        rendered_gate = MODULE["render_gate"](report)
        self.assertIn("t4_012=PASS", rendered_report)
        self.assertIn("t4_014=PASS_WITH_NOTES", rendered_report)
        self.assertIn("gate_decision=PASS_WITH_NOTES", rendered_gate)

    def test_full_report_fail_contains_reason_and_gate_failure(self) -> None:
        result = self._validate_full()
        failed = replace(result, status="FAIL", errors=("synthetic failure",))
        report = MODULE["Stage4ValidationReport"](
            (failed,), 0.494025, 1e-6, "fixture-config", 1, "fixture", "full"
        )
        rendered_report = MODULE["render_validation_report"](report)
        rendered_gate = MODULE["render_gate"](report)
        self.assertIn("errors=synthetic failure", rendered_report)
        self.assertIn("gate_decision=FAIL", rendered_gate)

    def test_full_distribution_summary_is_grouped_by_plan_and_month(self) -> None:
        result = self._validate_full()
        report = MODULE["Stage4ValidationReport"](
            (result,), 0.494025, 1e-6, "fixture-config", 1, "fixture", "full"
        )
        summary = MODULE["distribution_summary"](report)
        self.assertEqual(summary[0]["period"], "daily_jfm:02")
        self.assertEqual(summary[0]["variables"]["uo"]["files"], 1)

    def test_full_distribution_summary_flags_extreme_change(self) -> None:
        result = self._validate_full()
        altered = replace(
            result,
            job_id="daily_jfm_2021_02",
            distribution_metrics=tuple(
                (metric[0], metric[1], metric[2], metric[3], metric[4] + 2.0, metric[5], metric[6] + 2.0, metric[7] + 2.0, metric[8] + 2.0)
                for metric in result.distribution_metrics
            ),
            start_datetime="2021-02-01T00:00:00",
        )
        rows = tuple([result] * 4 + [altered])
        report = MODULE["Stage4ValidationReport"](
            rows, 0.494025, 1e-6, "fixture-config", 5, "fixture", "full"
        )
        summary = MODULE["distribution_summary"](report)
        flags = [flag for period in summary for flag in period["flags"]]
        self.assertTrue(flags)


if __name__ == "__main__":
    unittest.main()
