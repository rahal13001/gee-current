from __future__ import annotations

from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO


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
        self.assertIn("actual T3-014 download is disabled", output)

    def test_daily_full_remains_rejected(self) -> None:
        status, output = self._run_main("--plan", "daily_full", "--dry-run")
        self.assertEqual(status, 2)
        self.assertIn("daily_full is disabled", output)

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


if __name__ == "__main__":
    unittest.main()
