from __future__ import annotations

from pathlib import Path
import runpy
import tempfile
import unittest

from python.dataset_pin import (
    DatasetPin,
    DatasetPinError,
    build_manifest,
    load_dataset_pin,
    read_manifest,
    validate_batch_pin,
    validate_manifest_pin,
    write_manifest,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN_MODULE = runpy.run_path(str(ROOT / "python" / "02_build_download_plan.py"))


class Stage3DatasetPinTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pin = load_dataset_pin(ROOT)
        self.jobs = [
            {
                "job_id": "daily_jfm_2020_01",
                "dataset_version": "202311",
                "dataset_part": "default",
            },
            {
                "job_id": "daily_jfm_2020_02",
                "dataset_version": "202311",
                "dataset_part": "default",
            },
        ]

    def test_local_snapshot_provides_expected_pin(self) -> None:
        self.assertEqual(self.pin, DatasetPin("202311", "default"))

    def test_batch_pin_accepts_matching_jobs(self) -> None:
        self.assertEqual(tuple(validate_batch_pin(self.jobs, self.pin)), tuple(self.jobs))

    def test_download_plans_are_pinned_to_local_snapshot(self) -> None:
        for plan_name in ("monthly_all", "daily_jfm"):
            jobs = PLAN_MODULE["build_plan"](
                ROOT, plan_name, created_utc="2026-08-04T00:00:00Z"
            )
            self.assertEqual(tuple(validate_batch_pin(jobs, self.pin)), tuple(jobs))

    def test_batch_pin_rejects_version_change(self) -> None:
        changed = [*self.jobs, {**self.jobs[0], "job_id": "new", "dataset_version": "202402"}]
        with self.assertRaises(DatasetPinError):
            validate_batch_pin(changed, self.pin)

    def test_batch_pin_rejects_part_change(self) -> None:
        changed = [*self.jobs, {**self.jobs[0], "job_id": "new", "dataset_part": "alternate"}]
        with self.assertRaises(DatasetPinError):
            validate_batch_pin(changed, self.pin)

    def test_manifest_round_trip_and_pin_check(self) -> None:
        manifest = build_manifest(self.jobs, self.pin, created_utc="2026-08-04T00:00:00Z")
        self.assertEqual(manifest["job_ids"], ["daily_jfm_2020_01", "daily_jfm_2020_02"])
        validate_manifest_pin(manifest, self.pin)

        with tempfile.TemporaryDirectory() as folder:
            target = write_manifest(
                Path(folder) / "batch_pin.json",
                self.jobs,
                self.pin,
                created_utc="2026-08-04T00:00:00Z",
            )
            self.assertEqual(read_manifest(target), manifest)

    def test_manifest_change_is_fail_closed(self) -> None:
        manifest = build_manifest(self.jobs, self.pin, created_utc="2026-08-04T00:00:00Z")
        manifest["dataset_version"] = "202402"
        with self.assertRaises(DatasetPinError):
            validate_manifest_pin(manifest, self.pin)

    def test_invalid_snapshot_pin_is_rejected(self) -> None:
        with self.assertRaises(DatasetPinError):
            DatasetPin.from_snapshot({"metadata_version": "202311"})

    def test_empty_batch_is_rejected(self) -> None:
        with self.assertRaises(DatasetPinError):
            validate_batch_pin([], self.pin)


if __name__ == "__main__":
    unittest.main()
