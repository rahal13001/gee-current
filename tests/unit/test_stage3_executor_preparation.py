from __future__ import annotations

from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from python.inventory import InventoryStore


ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / "python" / "03_download_glorys.py"))


class Stage3ExecutorPreparationTests(unittest.TestCase):
    def _run_main(self, *arguments: str) -> tuple[int, str]:
        original_argv = sys.argv
        sys.argv = ["03_download_glorys.py", "--root", str(ROOT), *arguments]
        stdout = StringIO()
        try:
            with redirect_stdout(stdout):
                status = MODULE["main"]()
        finally:
            sys.argv = original_argv
        return status, stdout.getvalue()

    def test_monthly_dry_run_is_local_only(self) -> None:
        status, output = self._run_main("--plan", "monthly_all", "--dry-run")
        self.assertEqual(status, 0)
        self.assertIn("job_count=132", output)
        self.assertIn("expected_timesteps=132", output)
        self.assertIn("authentication=NOT_PERFORMED", output)
        self.assertIn("network=NOT_PERFORMED", output)
        self.assertIn("download=NOT_PERFORMED", output)
        self.assertIn("status=DRY_RUN_READY", output)

    def test_actual_mode_is_fail_closed(self) -> None:
        status, output = self._run_main("--plan", "monthly_all")
        self.assertEqual(status, 3)
        self.assertIn("requires explicit --execute", output)

    def test_subset_arguments_use_active_regional_aoi_and_pinned_depth(self) -> None:
        jobs, _ = MODULE["build_local_plan"](
            ROOT,
            "monthly_all",
            created_utc="2026-08-05T00:00:00Z",
        )
        job = MODULE["JobRecord"](**jobs[0])
        aoi, depth_m = MODULE["load_runtime_config"](ROOT)
        arguments = MODULE["build_subset_kwargs"](
            job,
            aoi=aoi,
            depth_m=depth_m,
            output_directory="data/partial/monthly_all/2015",
        )
        self.assertEqual(arguments["dataset_id"], "cmems_mod_glo_phy_my_0.083deg_P1M-m")
        self.assertEqual(arguments["dataset_version"], "202311")
        self.assertEqual(arguments["dataset_part"], "default")
        self.assertEqual(arguments["variables"], ["uo", "vo"])
        self.assertEqual(arguments["minimum_longitude"], 122.986190)
        self.assertEqual(arguments["maximum_longitude"], 143.326183)
        self.assertEqual(arguments["minimum_latitude"], -12.191592)
        self.assertEqual(arguments["maximum_latitude"], 4.265137)
        self.assertEqual(arguments["minimum_depth"], 0.494025)
        self.assertEqual(arguments["end_datetime"], arguments["start_datetime"])
        self.assertTrue(arguments["raise_if_updating"])

        daily_jobs, _ = MODULE["build_local_plan"](
            ROOT,
            "daily_jfm",
            created_utc="2026-08-05T00:00:00Z",
        )
        daily_job = MODULE["JobRecord"](**daily_jobs[0])
        daily_arguments = MODULE["build_subset_kwargs"](
            daily_job,
            aoi=aoi,
            depth_m=depth_m,
            output_directory="data/partial/daily_jfm/2015",
        )
        self.assertEqual(daily_job.expected_timesteps, 31)
        self.assertEqual(daily_arguments["end_datetime"], "2015-01-31T00:00:00")

    def test_permanent_failure_uses_legal_state_transitions(self) -> None:
        folder = tempfile.TemporaryDirectory(dir=ROOT)
        try:
            temporary_root = Path(folder.name).resolve()
            database = temporary_root.relative_to(ROOT.resolve()) / "inventory.sqlite"
            jobs, _ = MODULE["build_local_plan"](
                ROOT,
                "monthly_all",
                created_utc="2026-08-05T00:00:00Z",
            )
            with InventoryStore(ROOT / database) as store:
                store.seed_jobs([jobs[0]])
                store.transition(jobs[0]["job_id"], "preflight_passed")
                store.transition(jobs[0]["job_id"], "downloading", attempt_count=1)
                result = MODULE["_mark_failed_permanent"](store, jobs[0]["job_id"])
                self.assertEqual(result.status, "failed_permanent")
                reopened = store.requeue_failed_permanent(
                    jobs[0]["job_id"],
                    reason="unit-test manual retry",
                )
                self.assertEqual(reopened.status, "retry_wait")
        finally:
            folder.cleanup()

    def test_daily_full_remains_rejected(self) -> None:
        status, output = self._run_main("--plan", "daily_full", "--dry-run")
        self.assertEqual(status, 2)
        self.assertIn("daily_full is disabled", output)

    def test_execute_requires_explicit_non_dry_run_mode(self) -> None:
        status, output = self._run_main("--plan", "monthly_all", "--dry-run", "--execute")
        self.assertEqual(status, 2)
        self.assertIn("mutually exclusive", output)

    def test_prepare_inventory_seeds_and_then_preserves_existing_state(self) -> None:
        folder = tempfile.TemporaryDirectory(dir=ROOT)
        try:
            temporary_root = Path(folder.name).resolve()
            database = temporary_root.relative_to(ROOT.resolve()) / "inventory.sqlite"
            csv_path = temporary_root.relative_to(ROOT.resolve()) / "inventory.csv"
            jobs, summary = MODULE["build_local_plan"](
                ROOT,
                "daily_jfm",
                created_utc="2026-08-05T00:00:00Z",
            )
            count, seeded = MODULE["prepare_inventory"](
                ROOT,
                jobs,
                inventory_path=database,
                inventory_csv=csv_path,
            )
            self.assertEqual(summary.job_count, 33)
            self.assertEqual(summary.expected_timesteps, 993)
            self.assertEqual(count, 33)
            self.assertTrue(seeded)
            self.assertTrue(database.exists())
            self.assertTrue(csv_path.exists())

            count, seeded = MODULE["prepare_inventory"](
                ROOT,
                jobs,
                inventory_path=database,
                inventory_csv=csv_path,
            )
            self.assertEqual(count, 33)
            self.assertFalse(seeded)
        finally:
            folder.cleanup()

    def test_prepare_inventory_allows_multiple_plan_batches_in_one_database(self) -> None:
        folder = tempfile.TemporaryDirectory(dir=ROOT)
        try:
            temporary_root = Path(folder.name).resolve()
            database = temporary_root.relative_to(ROOT.resolve()) / "inventory.sqlite"
            csv_path = temporary_root.relative_to(ROOT.resolve()) / "inventory.csv"
            monthly, _ = MODULE["build_local_plan"](
                ROOT,
                "monthly_all",
                created_utc="2026-08-05T00:00:00Z",
            )
            daily, _ = MODULE["build_local_plan"](
                ROOT,
                "daily_jfm",
                created_utc="2026-08-05T00:00:00Z",
            )
            with InventoryStore(ROOT / database) as store:
                store.seed_jobs(monthly)

            count, seeded = MODULE["prepare_inventory"](
                ROOT,
                daily,
                inventory_path=database,
                inventory_csv=csv_path,
            )
            self.assertEqual(count, 165)
            self.assertTrue(seeded)
            with InventoryStore(ROOT / database) as store:
                self.assertEqual(len(store.list_jobs()), 165)
                self.assertEqual(
                    len(tuple(job for job in store.list_jobs() if job.plan_name == "monthly_all")),
                    132,
                )
                self.assertEqual(
                    len(tuple(job for job in store.list_jobs() if job.plan_name == "daily_jfm")),
                    33,
                )
        finally:
            folder.cleanup()


if __name__ == "__main__":
    unittest.main()
