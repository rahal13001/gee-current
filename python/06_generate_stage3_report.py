"""Generate the offline Stage 3 report and release gate.

The report consumes the approved local plans and the read-only T3-016
reconciliation. It does not authenticate, access credentials, contact a
service, download data, mutate inventory, or change repository status files.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import runpy
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PLAN_MODULE = runpy.run_path(str(Path(__file__).with_name("02_build_download_plan.py")))
build_plan = PLAN_MODULE["build_plan"]
PlanError = PLAN_MODULE["PlanError"]
RECONCILE_MODULE = runpy.run_path(str(Path(__file__).with_name("05_reconcile_inventory.py")))
reconcile = RECONCILE_MODULE["reconcile"]
ReconciliationError = RECONCILE_MODULE["ReconciliationError"]
ReconciliationReport = RECONCILE_MODULE["ReconciliationReport"]
DEFAULT_INVENTORY_PATH = RECONCILE_MODULE["DEFAULT_INVENTORY_PATH"]


class Stage3ReportError(ValueError):
    """Raised when the Stage 3 gate cannot be evaluated safely."""


@dataclass(frozen=True)
class Stage3GateReport:
    """All decision-relevant Stage 3 gate fields."""

    monthly_jobs: int
    daily_jobs: int
    monthly_timesteps: int
    daily_timesteps: int
    total_jobs: int
    total_timesteps: int
    inventory_jobs: int
    ready_jobs: int
    active_files: int
    checksum_matches: int
    quarantine_files: int
    partial_files: int
    dataset_versions: tuple[str, ...]
    dataset_parts: tuple[str, ...]
    aoi_name: str
    aoi_bounds: tuple[float, float, float, float]
    depth_m: float
    reconciliation_status: str
    issues: tuple[str, ...]

    @property
    def gate_decision(self) -> str:
        if self.reconciliation_status == "FAIL":
            return "FAIL"
        return "PASS_WITH_NOTES" if self.issues else "PASS"


def _read_json(root: Path, relative: str) -> dict[str, Any]:
    try:
        value = json.loads((root / relative).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise Stage3ReportError(f"cannot read local configuration: {relative}") from exc
    if not isinstance(value, dict):
        raise Stage3ReportError(f"local configuration must be an object: {relative}")
    return value


def _runtime_context(root: Path) -> tuple[str, tuple[float, float, float, float], float]:
    study = _read_json(root, "config/study_area.json")
    try:
        aoi_name = str(study["aoi_id"])
        bounds = (
            float(study["west"]),
            float(study["east"]),
            float(study["south"]),
            float(study["north"]),
        )
        depth = float(_read_json(root, "config/depth_selection.json")["analysis_depth_m"])
    except (KeyError, TypeError, ValueError) as exc:
        raise Stage3ReportError("active AOI/depth configuration is incomplete") from exc
    return aoi_name, bounds, depth


def _plan_rows(root: Path, plan_name: str) -> tuple[dict[str, Any], ...]:
    try:
        return tuple(build_plan(root, plan_name, created_utc="2026-08-05T00:00:00Z"))
    except (PlanError, OSError, ValueError) as exc:
        raise Stage3ReportError(f"cannot build {plan_name} plan: {exc}") from exc


def build_gate_report(
    root: str | Path,
    *,
    inventory_path: str | Path = DEFAULT_INVENTORY_PATH,
) -> Stage3GateReport:
    """Evaluate the Stage 3 gate from local plans and T3-016 reconciliation."""

    root_path = Path(root).resolve()
    monthly = _plan_rows(root_path, "monthly_all")
    daily = _plan_rows(root_path, "daily_jfm")
    reconciliation: ReconciliationReport = reconcile(
        root_path,
        inventory_path=inventory_path,
    )
    versions = tuple(sorted({str(row["dataset_version"]) for row in monthly + daily}))
    parts = tuple(sorted({str(row["dataset_part"]) for row in monthly + daily}))
    aoi_name, bounds, depth = _runtime_context(root_path)

    issues = tuple(
        f"{issue.severity}|{issue.code}|{issue.detail}"
        for issue in reconciliation.issues
        if issue.severity != "NOTE"
    )
    if reconciliation.quarantine_files:
        issues = issues + (
            "NOTE|QUARANTINE_ARTIFACTS|"
            f"{reconciliation.quarantine_files} quarantined NetCDF artifact(s) retained as audit evidence",
        )
    return Stage3GateReport(
        monthly_jobs=len(monthly),
        daily_jobs=len(daily),
        monthly_timesteps=sum(int(row["expected_timesteps"]) for row in monthly),
        daily_timesteps=sum(int(row["expected_timesteps"]) for row in daily),
        total_jobs=len(monthly) + len(daily),
        total_timesteps=sum(int(row["expected_timesteps"]) for row in monthly + daily),
        inventory_jobs=reconciliation.inventory_jobs,
        ready_jobs=reconciliation.ready_jobs,
        active_files=reconciliation.active_files,
        checksum_matches=reconciliation.checksum_matches,
        quarantine_files=reconciliation.quarantine_files,
        partial_files=reconciliation.partial_files,
        dataset_versions=versions,
        dataset_parts=parts,
        aoi_name=aoi_name,
        aoi_bounds=bounds,
        depth_m=depth,
        reconciliation_status=reconciliation.status,
        issues=issues,
    )


def render_report(report: Stage3GateReport) -> str:
    """Render a stable text report suitable for evidence capture."""

    west, east, south, north = report.aoi_bounds
    lines = [
        "stage=T3-017",
        "report_type=stage3_gate",
        f"monthly_jobs={report.monthly_jobs}",
        f"daily_jfm_jobs={report.daily_jobs}",
        f"total_jobs={report.total_jobs}",
        f"monthly_timesteps={report.monthly_timesteps}",
        f"daily_jfm_timesteps={report.daily_timesteps}",
        f"total_timesteps={report.total_timesteps}",
        f"inventory_jobs={report.inventory_jobs}",
        f"ready_jobs={report.ready_jobs}",
        f"active_files={report.active_files}",
        f"checksum_matches={report.checksum_matches}",
        f"partial_files={report.partial_files}",
        f"quarantine_files={report.quarantine_files}",
        f"dataset_versions={','.join(report.dataset_versions)}",
        f"dataset_parts={','.join(report.dataset_parts)}",
        f"aoi_name={report.aoi_name}",
        f"aoi_west={west}",
        f"aoi_east={east}",
        f"aoi_south={south}",
        f"aoi_north={north}",
        f"depth_m={report.depth_m}",
        "daily_full=DISABLED",
        f"reconciliation_status={report.reconciliation_status}",
        f"issue_count={len(report.issues)}",
    ]
    lines.extend(f"issue={issue}" for issue in report.issues)
    lines.append(f"gate_decision={report.gate_decision}")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY_PATH)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        report = build_gate_report(args.root, inventory_path=args.inventory)
        print(render_report(report))
        return 0 if report.gate_decision != "FAIL" else 4
    except (Stage3ReportError, ReconciliationError, OSError, ValueError) as exc:
        print("stage=T3-017")
        print(f"error={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
