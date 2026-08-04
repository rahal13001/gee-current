from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from python.inventory import InventoryStore
from python.resume import (
    ResumeAction,
    ResumeValidationError,
    build_resume_plan,
)


def _job(job_id: str) -> dict[str, object]:
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


def _move_to(store: InventoryStore, job_id: str, statuses: tuple[str, ...]) -> None:
    for status in statuses:
        store.transition(job_id, status)


class Stage3ResumeTests(unittest.TestCase):
    def test_interrupted_inventory_groups_completed_pending_retry_and_manual(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            with InventoryStore(Path(folder.name) / "inventory.sqlite") as store:
                jobs = [_job(f"job_{index}") for index in range(1, 7)]
                store.seed_jobs(jobs)
                _move_to(store, "job_1", ("preflight_passed", "downloading", "downloaded", "basic_check_passed", "checksum_recorded", "ready_for_stage4"))
                _move_to(store, "job_2", ("skipped_valid",))
                _move_to(store, "job_3", ("preflight_passed", "downloading"))
                _move_to(store, "job_4", ("preflight_passed", "downloading", "failed_retryable"))
                _move_to(store, "job_5", ("preflight_passed", "downloading", "failed_retryable", "retry_wait"))
                _move_to(store, "job_6", ("preflight_passed", "downloading", "failed_retryable", "failed_permanent"))

                plan = build_resume_plan(store.list_jobs())

                self.assertEqual(plan.job_ids(ResumeAction.SKIP_COMPLETED), ("job_1", "job_2"))
                self.assertEqual(plan.job_ids(ResumeAction.CONTINUE), ("job_3",))
                self.assertEqual(plan.job_ids(ResumeAction.RETRY), ("job_4", "job_5"))
                self.assertEqual(plan.job_ids(ResumeAction.MANUAL_REVIEW), ("job_6",))
                self.assertEqual(tuple(job.job_id for job in plan.actionable_jobs), ("job_3", "job_4", "job_5"))
        finally:
            folder.cleanup()

    def test_resume_is_idempotent_and_finished_jobs_are_not_actionable(self) -> None:
        jobs = tuple(
            type("Job", (), {"job_id": job_id, "status": status})()
            for job_id, status in (
                ("b", "ready_for_stage4"),
                ("a", "skipped_valid"),
                ("c", "planned"),
            )
        )
        first = build_resume_plan(jobs)
        second = build_resume_plan(jobs)
        self.assertEqual(first, second)
        self.assertEqual(first.job_ids(ResumeAction.SKIP_COMPLETED), ("a", "b"))
        self.assertEqual(first.job_ids(ResumeAction.CONTINUE), ("c",))
        self.assertEqual(first.actionable_jobs, first.continue_jobs)

    def test_file_without_checksum_is_not_marked_complete_by_resume(self) -> None:
        folder = tempfile.TemporaryDirectory()
        try:
            target = Path(folder.name) / "existing_without_checksum.nc"
            target.touch()
            with InventoryStore(Path(folder.name) / "inventory.sqlite") as store:
                store.seed_jobs([_job("job_without_hash")])
                plan = build_resume_plan(store.list_jobs())
                self.assertEqual(plan.job_ids(ResumeAction.CONTINUE), ("job_without_hash",))
                self.assertEqual(plan.job_ids(ResumeAction.SKIP_COMPLETED), ())
        finally:
            folder.cleanup()

    def test_duplicate_or_unknown_inventory_rows_fail_closed(self) -> None:
        base = _job("duplicate")
        duplicate = build_resume_plan
        with self.assertRaises(ResumeValidationError):
            duplicate(
                [
                    type("Job", (), base)(),
                    type("Job", (), base)(),
                ]
            )

        unknown = _job("unknown")
        unknown["status"] = "not_a_status"
        with self.assertRaises(ResumeValidationError):
            build_resume_plan([type("Job", (), unknown)()])


if __name__ == "__main__":
    unittest.main()
