from pathlib import Path
import unittest

from python.common.config_loader import ConfigError, load_m1_config


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
            text = study.read_text(encoding="utf-8").replace(
                '"west": 129.199367', '"west": 133.329067'
            )
            study.write_text(
                text.replace('"east": 133.329067', '"east": 129.199367'),
                encoding="utf-8",
            )
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
