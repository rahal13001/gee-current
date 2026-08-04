from __future__ import annotations

from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / "python" / "02_build_download_plan.py"))


class Stage3PlanBuilderTests(unittest.TestCase):
    def test_monthly_plan_has_132_unique_jobs(self) -> None:
        jobs = MODULE["build_plan"](ROOT, "monthly_all", created_utc="2026-08-04T00:00:00Z")
        self.assertEqual(len(jobs), 132)
        self.assertEqual(sum(job["expected_timesteps"] for job in jobs), 132)
        self.assertEqual(len({job["job_id"] for job in jobs}), 132)
        self.assertEqual(jobs[0]["job_id"], "monthly_2015_01")
        self.assertEqual(jobs[-1]["job_id"], "monthly_2025_12")

    def test_daily_jfm_plan_has_993_timesteps(self) -> None:
        jobs = MODULE["build_plan"](ROOT, "daily_jfm", created_utc="2026-08-04T00:00:00Z")
        self.assertEqual(len(jobs), 33)
        self.assertEqual(sum(job["expected_timesteps"] for job in jobs), 993)
        february_2020 = next(job for job in jobs if job["job_id"] == "daily_jfm_2020_02")
        self.assertEqual(february_2020["expected_timesteps"], 29)
        self.assertEqual(february_2020["end_datetime"], "2020-02-29T23:59:59")

    def test_daily_full_is_fail_closed(self) -> None:
        with self.assertRaises(MODULE["PlanError"]):
            MODULE["build_plan"](ROOT, "daily_full")


if __name__ == "__main__":
    unittest.main()
