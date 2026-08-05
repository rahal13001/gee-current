from __future__ import annotations

from pathlib import Path
import runpy
import tempfile
import unittest

from python.checksum import sha256_file
from python.inventory import InventoryStore


ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / "python" / "05_reconcile_inventory.py"))


def _job(job_id: str, plan_name: str, filename: str) -> dict[str, object]:
    daily = plan_name == "daily_jfm"
    return {
        "job_id": job_id,
        "plan_name": plan_name,
        "dataset_id": "cmems_mod_glo_phy_my_0.083deg_P1D-m" if daily else "cmems_mod_glo_phy_my_0.083deg_P1M-m",
        "year": 2015,
        "month": 1,
        "start_datetime": "2015-01-01T00:00:00",
        "end_datetime": "2015-01-31T23:59:59",
        "expected_timesteps": 31 if daily else 1,
        "output_directory": f"data/raw/{'daily_jfm' if daily else 'monthly'}/2015",
        "output_filename": filename,
        "status": "planned",
        "attempt_count": 0,
        "checksum": "",
        "dataset_version": "202311",
        "dataset_part": "default",
        "created_utc": "2026-08-05T00:00:00Z",
    }


class Stage3ReconcileInventoryTests(unittest.TestCase):
    def _ready(self, store: InventoryStore, job_id: str, checksum: str) -> None:
        store.transition(job_id, "preflight_passed")
        store.transition(job_id, "downloading", attempt_count=1)
        store.transition(job_id, "downloaded")
        store.transition(job_id, "basic_check_passed")
        store.transition(job_id, "checksum_recorded", checksum=checksum)
        store.transition(job_id, "ready_for_stage4", checksum=checksum)

    def _with_fixture_plan(self, rows: list[dict[str, object]], callback):
        namespace = MODULE["reconcile"].__globals__
        original = namespace["_expected_plan"]
        namespace["_expected_plan"] = lambda _root, plan_name: tuple(
            row for row in rows if row["plan_name"] == plan_name
        )
        try:
            return callback()
        finally:
            namespace["_expected_plan"] = original

    def test_reconcile_passes_shared_monthly_and_daily_inventory(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            root = Path(folder.name)
            monthly = _job("monthly_2015_01", "monthly_all", "monthly.nc")
            daily = _job("daily_jfm_2015_01", "daily_jfm", "daily.nc")
            monthly_path = root / monthly["output_directory"] / monthly["output_filename"]
            daily_path = root / daily["output_directory"] / daily["output_filename"]
            monthly_path.parent.mkdir(parents=True)
            daily_path.parent.mkdir(parents=True)
            monthly_path.write_bytes(b"monthly")
            daily_path.write_bytes(b"daily")
            with InventoryStore(root / "inventory.sqlite") as store:
                store.seed_jobs([monthly, daily])
                self._ready(store, "monthly_2015_01", sha256_file(monthly_path))
                self._ready(store, "daily_jfm_2015_01", sha256_file(daily_path))

            report = self._with_fixture_plan(
                [monthly, daily],
                lambda: MODULE["reconcile"](root, inventory_path="inventory.sqlite"),
            )
            self.assertEqual(report.status, "PASS")
            self.assertEqual(report.expected_jobs, 2)
            self.assertEqual(report.inventory_jobs, 2)
            self.assertEqual(report.ready_jobs, 2)
            self.assertEqual(report.active_files, 2)
            self.assertEqual(report.checksum_matches, 2)
        finally:
            folder.cleanup()

    def test_reconcile_flags_missing_extra_and_checksum_mismatch(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            root = Path(folder.name)
            first = _job("monthly_2015_01", "monthly_all", "first.nc")
            second = _job("monthly_2015_02", "monthly_all", "second.nc")
            output = root / "data/raw/monthly/2015"
            output.mkdir(parents=True)
            first_path = output / "first.nc"
            extra_path = output / "extra.nc"
            first_path.write_bytes(b"changed")
            extra_path.write_bytes(b"extra")
            with InventoryStore(root / "inventory.sqlite") as store:
                store.seed_jobs([first, second])
                self._ready(store, "monthly_2015_01", "0" * 64)
                self._ready(store, "monthly_2015_02", "1" * 64)

            report = self._with_fixture_plan(
                [first, second],
                lambda: MODULE["reconcile"](
                    root,
                    plan_name="monthly_all",
                    inventory_path="inventory.sqlite",
                ),
            )
            codes = {issue.code for issue in report.issues}
            self.assertEqual(report.status, "FAIL")
            self.assertIn("ACTIVE_FILE_MISSING", codes)
            self.assertIn("ACTIVE_FILE_EXTRA", codes)
            self.assertIn("CHECKSUM_MISMATCH", codes)
        finally:
            folder.cleanup()


if __name__ == "__main__":
    unittest.main()
