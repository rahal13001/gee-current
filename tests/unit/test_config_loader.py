from pathlib import Path
import json
import unittest

from python.common.config_loader import ConfigError, load_m1_config
from python.common.depth_metadata import (
    DepthMetadataError,
    extract_depth_levels,
    validate_depth_levels,
)
from python.common.descriptive_statistics import StatisticsError, summary_statistics
from python.common.metadata_guard import compare_metadata
from python.common.scientific_formulas import FormulaError, resultant_direction, vector_statistics


CONFIG_ROOT = Path(__file__).parents[2] / "config"


class ConfigLoaderTests(unittest.TestCase):
    def copy_config(self, destination: Path) -> None:
        destination.mkdir(exist_ok=True)
        for source in CONFIG_ROOT.glob("*.json"):
            (destination / source.name).write_text(
                source.read_text(encoding="utf-8"), encoding="utf-8"
            )

    def test_loads_approved_offline_configuration(self):
        config = load_m1_config(CONFIG_ROOT)
        self.assertLess(config.study_area.west, config.study_area.east)
        self.assertLess(config.study_area.south, config.study_area.north)
        self.assertTrue(
            config.project.asset_root.startswith(
                f"projects/{config.project.project_id}/assets/"
            )
        )
        self.assertEqual(config.period["monthly_count_expected"], 132)
        self.assertEqual(config.period["daily_jfm_count_expected"], 993)

    def test_reversed_study_area_fails_closed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            self.copy_config(destination)
            study = destination / "study_area.json"
            study_data = json.loads(study.read_text(encoding="utf-8"))
            study_data["west"], study_data["east"] = (
                study_data["east"],
                study_data["west"],
            )
            study.write_text(json.dumps(study_data), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "west < east"):
                load_m1_config(destination)

    def test_project_asset_mismatch_fails_closed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            self.copy_config(destination)
            local = destination / "local.example.json"
            text = local.read_text(encoding="utf-8").replace(
                "projects/ee-rahal13001/assets/glorys_current",
                "projects/another-project/assets/glorys_current",
            )
            local.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "asset root does not belong"):
                load_m1_config(destination)

    def test_statistics_and_period_drift_fail_closed(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            self.copy_config(destination)
            statistics = destination / "statistics.json"
            text = statistics.read_text(encoding="utf-8").replace(
                '"threshold_status": "RESOLVED_GLOBAL_AOI_P90"',
                '"threshold_status": "invented"',
            )
            statistics.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "threshold status"):
                load_m1_config(destination)

    def test_resolved_current_rose_contract_fails_closed_on_drift(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder)
            self.copy_config(destination)
            statistics = destination / "statistics.json"
            data = json.loads(statistics.read_text(encoding="utf-8"))
            data["current_rose"]["sector_count"] = 8
            statistics.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ConfigError, "16 sectors"):
                load_m1_config(destination)

    def test_metadata_guard_accepts_approved_snapshot(self):
        snapshot_path = (
            Path(__file__).parents[2]
            / "outputs"
            / "evidence"
            / "stage_0"
            / "metadata_snapshot_2026-08-02.json"
        )
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertEqual(compare_metadata(snapshot, snapshot), ())

    def test_metadata_guard_fails_on_dataset_change(self):
        snapshot_path = (
            Path(__file__).parents[2]
            / "outputs"
            / "evidence"
            / "stage_0"
            / "metadata_snapshot_2026-08-02.json"
        )
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        candidate = json.loads(json.dumps(snapshot))
        candidate["datasets"]["daily"]["id"] = "unexpected-dataset"
        changes = compare_metadata(snapshot, candidate)
        self.assertTrue(any(change.path == "datasets.daily.id" for change in changes))

    def test_depth_validator_requires_fifty_monotonic_levels(self):
        levels = tuple(0.494025 + (index * 10.0) for index in range(50))
        validate_depth_levels(levels)
        validate_depth_levels(tuple(reversed(levels)))
        with self.assertRaises(DepthMetadataError):
            validate_depth_levels(levels[:-1])
        with self.assertRaises(DepthMetadataError):
            extract_depth_levels({"depth": {"full_50_level_extraction": "NOT_RUN"}})

    def test_scientific_formulas_cover_cardinals_and_persistence(self):
        self.assertEqual(resultant_direction(0, 1), 0.0)
        self.assertEqual(resultant_direction(1, 0), 90.0)
        self.assertEqual(resultant_direction(0, -1), 180.0)
        self.assertEqual(resultant_direction(-1, 0), 270.0)

        stats = vector_statistics((1.0, -1.0), (0.0, 0.0))
        self.assertEqual(stats["mean_speed"], 1.0)
        self.assertEqual(stats["resultant_speed"], 0.0)
        self.assertEqual(stats["persistence_index"], 0.0)
        self.assertIsNone(stats["resultant_direction"])

    def test_scientific_formulas_fail_closed(self):
        with self.assertRaises(FormulaError):
            vector_statistics((1.0,), (1.0, 2.0))
        with self.assertRaises(FormulaError):
            vector_statistics((float("nan"),), (0.0,))
        self.assertIsNone(vector_statistics((0.0,), (0.0,))["persistence_index"])

    def test_descriptive_statistics_use_explicit_parameters(self):
        stats = summary_statistics(
            (1.0, 2.0, 3.0, 4.0), ddof=0, percentile_method="linear"
        )
        self.assertEqual(stats["count"], 4)
        self.assertEqual(stats["median"], 2.5)
        self.assertAlmostEqual(stats["variance"], 1.25)
        self.assertAlmostEqual(stats["p10"], 1.3)
        self.assertAlmostEqual(stats["p99"], 3.97)

    def test_descriptive_statistics_fail_closed_without_method_choice(self):
        with self.assertRaises(StatisticsError):
            summary_statistics((1.0, 2.0), ddof=0, percentile_method="nearest")
        with self.assertRaises(StatisticsError):
            summary_statistics((1.0,), ddof=1, percentile_method="linear")
