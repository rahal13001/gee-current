from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from python.inventory import InventoryStore
from python.quarantine import (
    QuarantineCollisionError,
    QuarantineError,
    quarantine_file,
    quarantine_job,
)


def _job(job_id: str = "job_001") -> dict[str, object]:
    return {
        "job_id": job_id,
        "plan_name": "monthly_all",
        "dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1M-m",
        "year": 2015,
        "month": 1,
        "start_datetime": "2015-01-01T00:00:00",
        "end_datetime": "2015-01-31T23:59:59",
        "expected_timesteps": 1,
        "output_directory": "data/raw/monthly/2015",
        "output_filename": f"{job_id}.nc",
        "status": "planned",
        "attempt_count": 0,
        "checksum": "",
        "dataset_version": "202311",
        "dataset_part": "default",
        "created_utc": "2026-08-04T00:00:00Z",
    }


class Stage3QuarantineTests(unittest.TestCase):
    def test_invalid_file_moves_atomically_and_reason_json_is_traceable(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            root = Path(folder.name)
            source = root / "data/raw/glorys12v1_daily_202002.nc"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"corrupt fixture")

            record = quarantine_file(
                source,
                root=root,
                job_id="daily_jfm_2020_02",
                reason="time_count_mismatch",
                expected=29,
                actual=28,
                quarantined_utc="20260731T011500Z",
            )

            self.assertFalse(source.exists())
            destination = root / record.quarantine_relative_path
            reason_path = root / record.reason_relative_path
            self.assertTrue(destination.is_file())
            self.assertTrue(reason_path.is_file())
            self.assertEqual(destination.read_bytes(), b"corrupt fixture")
            self.assertEqual(
                json.loads(reason_path.read_text(encoding="utf-8")),
                {
                    "actual": 28,
                    "expected": 29,
                    "job_id": "daily_jfm_2020_02",
                    "quarantine_relative_path": record.quarantine_relative_path,
                    "quarantined_utc": "20260731T011500Z",
                    "reason": "time_count_mismatch",
                    "source_relative_path": "data/raw/glorys12v1_daily_202002.nc",
                },
            )
        finally:
            folder.cleanup()

    def test_destination_collision_fails_without_overwrite_or_source_loss(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            root = Path(folder.name)
            source = root / "data/raw/file.nc"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"original")
            collision = root / "data/quarantine/20260731T011500Z"
            collision.mkdir(parents=True)
            (collision / "reason.json").write_text("keep", encoding="utf-8")

            with self.assertRaises(QuarantineCollisionError):
                quarantine_file(
                    source,
                    root=root,
                    job_id="job_001",
                    reason="corrupt_file",
                    quarantined_utc="20260731T011500Z",
                )
            self.assertTrue(source.exists())
            self.assertEqual((collision / "reason.json").read_text(encoding="utf-8"), "keep")
        finally:
            folder.cleanup()

    def test_inventory_job_quarantine_does_not_mutate_inventory(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            root = Path(folder.name)
            output = root / "data/raw/monthly/2015/job_001.nc"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"bad fixture")
            with InventoryStore(root / "inventory.sqlite") as store:
                store.seed_jobs([_job()])
                record = quarantine_job(
                    store.get_job("job_001"),
                    root=root,
                    reason="checksum_mismatch",
                    quarantined_utc="20260731T011501Z",
                )
                self.assertEqual(store.get_job("job_001").status, "planned")
                self.assertTrue((root / record.quarantine_relative_path).is_file())
        finally:
            folder.cleanup()

    def test_path_escape_missing_file_and_invalid_metadata_fail_closed(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            root = Path(folder.name)
            outside = root.parent / f"outside-{root.name}.nc"
            outside.write_bytes(b"outside")
            with self.assertRaises(QuarantineError):
                quarantine_file(
                    outside,
                    root=root,
                    job_id="job_001",
                    reason="corrupt_file",
                    quarantined_utc="20260731T011502Z",
                )
            with self.assertRaises(QuarantineError):
                quarantine_file(
                    root / "missing.nc",
                    root=root,
                    job_id="job_001",
                    reason="corrupt_file",
                    quarantined_utc="20260731T011503Z",
                )
            source = root / "data/raw/file.nc"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"fixture")
            with self.assertRaises(QuarantineError):
                quarantine_file(
                    source,
                    root=root,
                    job_id="job_001",
                    reason="",
                    quarantined_utc="20260731T011504Z",
                )
            with self.assertRaises(QuarantineError):
                quarantine_file(
                    source,
                    root=root,
                    job_id="job_001",
                    reason="corrupt_file",
                    quarantined_utc="not-a-timestamp",
                )
        finally:
            outside.unlink(missing_ok=True)
            folder.cleanup()


if __name__ == "__main__":
    unittest.main()
