from __future__ import annotations

from pathlib import Path
import runpy
import unittest


ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / "python" / "06_generate_stage3_report.py"))


class Stage3ReportTests(unittest.TestCase):
    def test_render_report_contains_gate_fields_and_note(self) -> None:
        report = MODULE["Stage3GateReport"](
            monthly_jobs=132,
            daily_jobs=33,
            monthly_timesteps=132,
            daily_timesteps=993,
            total_jobs=165,
            total_timesteps=1125,
            inventory_jobs=165,
            ready_jobs=165,
            active_files=165,
            checksum_matches=165,
            quarantine_files=3,
            partial_files=0,
            dataset_versions=("202311",),
            dataset_parts=("default",),
            aoi_name="eastern_indonesia_regional_001",
            aoi_bounds=(122.986190, 143.326183, -12.191592, 4.265137),
            depth_m=0.494025,
            reconciliation_status="PASS_WITH_NOTES",
            issues=("NOTE|QUARANTINE_ARTIFACTS|3 retained",),
        )
        output = MODULE["render_report"](report)
        self.assertIn("stage=T3-017", output)
        self.assertIn("total_jobs=165", output)
        self.assertIn("total_timesteps=1125", output)
        self.assertIn("daily_full=DISABLED", output)
        self.assertIn("gate_decision=PASS_WITH_NOTES", output)

    def test_gate_report_fails_when_reconciliation_fails(self) -> None:
        report = MODULE["Stage3GateReport"](
            monthly_jobs=132,
            daily_jobs=33,
            monthly_timesteps=132,
            daily_timesteps=993,
            total_jobs=165,
            total_timesteps=1125,
            inventory_jobs=164,
            ready_jobs=164,
            active_files=164,
            checksum_matches=163,
            quarantine_files=3,
            partial_files=1,
            dataset_versions=("202311",),
            dataset_parts=("default",),
            aoi_name="eastern_indonesia_regional_001",
            aoi_bounds=(122.986190, 143.326183, -12.191592, 4.265137),
            depth_m=0.494025,
            reconciliation_status="FAIL",
            issues=("ERROR|CHECKSUM_MISMATCH|job",),
        )
        self.assertEqual(report.gate_decision, "FAIL")


if __name__ == "__main__":
    unittest.main()
