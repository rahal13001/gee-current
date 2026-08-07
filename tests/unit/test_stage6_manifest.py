from __future__ import annotations

import unittest
from pathlib import Path

from python.gee_manifest import ManifestError, build_sample_manifests, write_sample_manifests


ROOT = Path(__file__).resolve().parents[2]


class Stage6ManifestTests(unittest.TestCase):
    def test_builds_one_source_and_one_derived_sample_from_stage5_evidence(self) -> None:
        samples = build_sample_manifests(
            ROOT,
            gcs_bucket="t6-004-sample-bucket",
            created_utc="2026-08-06T00:00:00Z",
        )

        self.assertEqual(set(samples), {"source", "derived"})
        source = samples["source"]
        derived = samples["derived"]
        self.assertEqual(source["asset_role"], "source")
        self.assertTrue(source["name"].endswith("glorys12v1_d_20150101_d0p494025m"))
        self.assertEqual(source["bands"][0]["id"], "uo")
        self.assertEqual(source["bands"][1]["id"], "vo")
        self.assertEqual(source["properties"]["period_end_inclusive"], False)
        self.assertEqual(source["properties"]["source_filename"], "glorys12v1_daily_201501_d0p494025m.nc")
        self.assertEqual(derived["asset_role"], "derived")
        self.assertTrue(derived["name"].endswith("glorys12v1_speed_20150101_d0p494025m"))
        self.assertEqual(derived["properties"]["product_type"], "speed")
        self.assertEqual(derived["properties"]["plan_name"], "daily_jfm")
        self.assertEqual(derived["properties"]["units"], "m s-1")
        self.assertEqual(len(derived["bands"]), 1)

    def test_source_and_derived_samples_share_period_grid_and_mask_contract(self) -> None:
        samples = build_sample_manifests(
            ROOT,
            gcs_bucket="t6-004-sample-bucket",
            created_utc="2026-08-06T00:00:00Z",
        )

        source = samples["source"]
        derived = samples["derived"]
        self.assertEqual(source["startTime"], derived["startTime"])
        self.assertEqual(source["endTime"], derived["endTime"])
        self.assertEqual(source["properties"]["source_grid"], derived["properties"]["source_grid"])
        self.assertEqual(source["properties"]["source_checksum"].__class__, str)
        self.assertEqual(len(derived["properties"]["derived_checksum"]), 64)
        self.assertEqual(len(derived["properties"]["mask_checksum"]), 64)

    def test_bucket_is_required_to_avoid_silent_upload_placeholder(self) -> None:
        with self.assertRaises(ManifestError):
            build_sample_manifests(ROOT, gcs_bucket="", created_utc="2026-08-06T00:00:00Z")

    def test_writes_two_manifests_and_index_without_upload_commands(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_dir = Path(temporary) / "stage_6_t6_004"
            index = write_sample_manifests(
                ROOT,
                output_dir=output_dir,
                gcs_bucket="t6-004-sample-bucket",
                created_utc="2026-08-06T00:00:00Z",
            )
            self.assertEqual(index["stage"], "T6-004")
            self.assertEqual(index["sample_count"], 2)
            self.assertTrue((output_dir / "source_daily_jfm_20150101.json").is_file())
            self.assertTrue((output_dir / "derived_speed_daily_jfm_20150101.json").is_file())
            self.assertTrue((output_dir / "manifest_index.json").is_file())
            self.assertFalse((output_dir / "upload_commands.txt").exists())


if __name__ == "__main__":
    unittest.main()
