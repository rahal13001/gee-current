from __future__ import annotations

import csv
from pathlib import Path
import sqlite3
import tempfile
import unittest

import runpy

from python.inventory import (
    INVENTORY_COLUMNS,
    InventoryStore,
    InventoryTransitionError,
    InventoryValidationError,
    STATUSES,
)


def _job(job_id: str = "monthly_2015_01") -> dict[str, object]:
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
        "output_filename": "glorys12v1_monthly_201501_d0p494025m.nc",
        "status": "planned",
        "attempt_count": 0,
        "checksum": "",
        "dataset_version": "202311",
        "dataset_part": "default",
        "created_utc": "2026-08-04T00:00:00Z",
    }


class Stage3InventoryTests(unittest.TestCase):
    def make_store(self) -> tuple[tempfile.TemporaryDirectory[str], InventoryStore]:
        folder = tempfile.TemporaryDirectory()
        store = InventoryStore(Path(folder.name) / "inventory.sqlite")
        store.open()
        store.seed_jobs([_job()])
        return folder, store

    def tearDown(self) -> None:
        if hasattr(self, "store"):
            self.store.close()
        if hasattr(self, "folder"):
            self.folder.cleanup()

    def test_schema_contains_required_columns_and_all_states(self) -> None:
        self.folder, self.store = self.make_store()
        columns = tuple(
            row[1]
            for row in self.store.connection.execute(
                "PRAGMA table_info(download_inventory)"
            ).fetchall()
        )
        self.assertEqual(columns, INVENTORY_COLUMNS)
        self.assertEqual(len(STATUSES), 12)
        self.assertEqual(self.store.get_job("monthly_2015_01").status, "planned")

    def test_valid_main_path_reaches_stage4(self) -> None:
        self.folder, self.store = self.make_store()
        for status in (
            "preflight_passed",
            "downloading",
            "downloaded",
            "basic_check_passed",
            "checksum_recorded",
            "ready_for_stage4",
        ):
            self.store.transition("monthly_2015_01", status)
        record = self.store.get_job("monthly_2015_01")
        self.assertIsNotNone(record)
        self.assertEqual(record.status, "ready_for_stage4")

    def test_valid_retry_quarantine_and_skip_paths(self) -> None:
        self.folder, self.store = self.make_store()
        self.store.seed_jobs([_job("daily_jfm_2020_02"), _job("monthly_2015_02")])

        retry_path = (
            "daily_jfm_2020_02",
            ("preflight_passed", "downloading", "failed_retryable", "retry_wait", "downloading"),
        )
        for status in retry_path[1]:
            self.store.transition(retry_path[0], status)
        self.assertEqual(self.store.get_job(retry_path[0]).status, "downloading")

        self.store.transition("monthly_2015_02", "preflight_passed")
        self.store.transition("monthly_2015_02", "downloading")
        self.store.transition("monthly_2015_02", "downloaded")
        self.store.transition("monthly_2015_02", "quarantined")
        self.store.transition("monthly_2015_02", "downloading")
        self.assertEqual(self.store.get_job("monthly_2015_02").status, "downloading")

        self.store.seed_jobs([_job("monthly_2015_03")])
        self.store.transition("monthly_2015_03", "skipped_valid")
        self.store.transition("monthly_2015_03", "ready_for_stage4")

    def test_illegal_transition_is_rejected_and_state_is_unchanged(self) -> None:
        self.folder, self.store = self.make_store()
        for status in ("preflight_passed", "downloading", "downloaded"):
            self.store.transition("monthly_2015_01", status)
        with self.assertRaises(InventoryTransitionError):
            self.store.transition("monthly_2015_01", "ready_for_stage4")
        self.assertEqual(self.store.get_job("monthly_2015_01").status, "downloaded")

    def test_sqlite_trigger_rejects_direct_illegal_update(self) -> None:
        self.folder, self.store = self.make_store()
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.connection.execute(
                "UPDATE download_inventory SET status = 'ready_for_stage4' "
                "WHERE job_id = 'monthly_2015_01'"
            )
        self.assertEqual(self.store.get_job("monthly_2015_01").status, "planned")

    def test_new_job_must_start_planned(self) -> None:
        self.folder, self.store = self.make_store()
        invalid = _job("monthly_2015_04")
        invalid["status"] = "downloaded"
        with self.assertRaises(InventoryValidationError):
            self.store.seed_jobs([invalid])

    def test_csv_export_matches_sqlite_rows_and_header(self) -> None:
        self.folder, self.store = self.make_store()
        self.store.seed_jobs([_job("daily_jfm_2020_02")])
        self.store.transition("daily_jfm_2020_02", "preflight_passed")
        output = Path(self.folder.name) / "download_inventory.csv"

        self.assertEqual(self.store.export_csv(output), output)
        with output.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)

        self.assertEqual(reader.fieldnames, list(INVENTORY_COLUMNS))
        expected = [
            {
                column: str(getattr(job, column))
                for column in INVENTORY_COLUMNS
            }
            for job in self.store.list_jobs()
        ]
        self.assertEqual(rows, expected)

    def test_local_plan_builder_rows_can_be_seeded(self) -> None:
        root = Path(__file__).resolve().parents[2]
        plan_module = runpy.run_path(str(root / "python" / "02_build_download_plan.py"))
        monthly = plan_module["build_plan"](
            root, "monthly_all", created_utc="2026-08-04T00:00:00Z"
        )
        daily_jfm = plan_module["build_plan"](
            root, "daily_jfm", created_utc="2026-08-04T00:00:00Z"
        )
        folder = tempfile.TemporaryDirectory()
        try:
            with InventoryStore(Path(folder.name) / "plan_inventory.sqlite") as store:
                store.seed_jobs(monthly)
                self.assertEqual(len(store.list_jobs()), 132)
                self.assertEqual(sum(job.expected_timesteps for job in store.list_jobs()), 132)
            with InventoryStore(Path(folder.name) / "jfm_inventory.sqlite") as store:
                store.seed_jobs(daily_jfm)
                self.assertEqual(len(store.list_jobs()), 33)
                self.assertEqual(sum(job.expected_timesteps for job in store.list_jobs()), 993)
        finally:
            folder.cleanup()


if __name__ == "__main__":
    unittest.main()
