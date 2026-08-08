from __future__ import annotations

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from python.t6_publish_manifest import ManifestError, build_publish_manifest, write_publish_manifest


ROOT = Path(__file__).resolve().parents[2]


class Stage6PublishManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = build_publish_manifest(ROOT, created_utc="2026-08-07T00:00:00Z")

    def test_selects_core_source_and_derived_counts(self) -> None:
        manifest = self.manifest
        self.assertEqual(manifest["stage"], "T6-007/T6-008")
        self.assertEqual(manifest["source"]["selected_count"], 1125)
        self.assertEqual(manifest["derived"]["selected_count"], 1138)
        self.assertEqual(manifest["source"]["groups"]["monthly_all"]["count"], 132)
        self.assertEqual(manifest["source"]["groups"]["daily_jfm"]["count"], 993)
        self.assertEqual(manifest["derived"]["groups"]["speed"]["count"], 1125)
        self.assertEqual(manifest["derived"]["groups"]["monthly_climatology_speed"]["count"], 12)
        self.assertEqual(manifest["derived"]["groups"]["jfm_climatology_speed"]["count"], 1)

    def test_selection_is_collision_safe_and_deferred_products_are_explicit(self) -> None:
        manifest = self.manifest
        ids = [asset["target_asset_id"] for section in ("source", "derived") for asset in manifest[section]["assets"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any("/speed/daily_jfm/" in value for value in ids))
        self.assertTrue(any("/speed/monthly_all/" in value for value in ids))
        deferred = {entry["category"]: entry["local_count"] for entry in manifest["deferred"]}
        self.assertEqual(deferred["speed_anomaly"], 1125)
        self.assertEqual(deferred["exploratory_trend_slope"], 1)
        self.assertFalse(manifest["staging"]["upload_commands_generated"])

    def test_monthly_source_and_speed_carry_explicit_exclusive_time_window(self) -> None:
        manifest = self.manifest
        monthly_source = next(
            asset
            for asset in manifest["source"]["assets"]
            if asset["job_id"] == "monthly_2015_04"
        )
        monthly_speed = next(
            asset
            for asset in manifest["derived"]["assets"]
            if asset["product_type"] == "speed" and asset["job_id"] == "monthly_2015_04"
        )

        expected = {
            "startTime": "2015-04-01T00:00:00Z",
            "endTime": "2015-05-01T00:00:00Z",
        }
        self.assertEqual({key: monthly_source[key] for key in expected}, expected)
        self.assertEqual({key: monthly_speed[key] for key in expected}, expected)

    def test_manifest_matches_schema_and_write_refuses_overwrite(self) -> None:
        manifest = self.manifest
        schema = json.loads((ROOT / "config/gee_publish_selection.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        validator.validate(manifest)
        invalid = deepcopy(manifest)
        speed_asset = next(
            asset for asset in invalid["derived"]["assets"] if asset["product_type"] == "speed"
        )
        speed_asset.pop("startTime")
        with self.assertRaises(ValidationError):
            validator.validate(invalid)
        with TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_dir = Path(temporary) / "stage_6_publish"
            result = write_publish_manifest(ROOT, output_dir=output_dir, created_utc="2026-08-07T00:00:00Z")
            self.assertEqual(result["stage"], "T6-007/T6-008")
            with self.assertRaises(ManifestError):
                write_publish_manifest(ROOT, output_dir=output_dir, created_utc="2026-08-07T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
