"""Offline resume planning from the Stage 3 SQLite inventory.

This module plans what a future executor may do after an interruption.  It
does not inspect target files, compute checksums, mutate inventory rows, sleep,
authenticate, access network, or download data.  A file that exists without a
validated inventory status is therefore not treated as complete.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from python.inventory import JobRecord, STATUSES


class ResumeAction(str, Enum):
    """Safe action categories for an inventory-backed resume plan."""

    SKIP_COMPLETED = "skip_completed"
    CONTINUE = "continue"
    RETRY = "retry"
    MANUAL_REVIEW = "manual_review"


class ResumeValidationError(ValueError):
    """Raised when inventory rows cannot form a deterministic resume plan."""


COMPLETED_STATUSES = frozenset({"ready_for_stage4", "skipped_valid"})
CONTINUE_STATUSES = frozenset(
    {
        "planned",
        "preflight_passed",
        "downloading",
        "downloaded",
        "basic_check_passed",
        "checksum_recorded",
    }
)
RETRY_STATUSES = frozenset({"retry_wait", "failed_retryable"})
MANUAL_REVIEW_STATUSES = frozenset({"failed_permanent", "quarantined"})


@dataclass(frozen=True)
class ResumePlan:
    """Deterministic grouping of inventory jobs for a future resume."""

    skip_completed: tuple[JobRecord, ...]
    continue_jobs: tuple[JobRecord, ...]
    retry_jobs: tuple[JobRecord, ...]
    manual_review: tuple[JobRecord, ...]

    @property
    def actionable_jobs(self) -> tuple[JobRecord, ...]:
        """Return unfinished jobs that a future executor may consider."""

        return tuple(
            sorted(
                self.continue_jobs + self.retry_jobs,
                key=lambda job: job.job_id,
            )
        )

    def job_ids(self, action: ResumeAction) -> tuple[str, ...]:
        """Return deterministic IDs for one action category."""

        groups = {
            ResumeAction.SKIP_COMPLETED: self.skip_completed,
            ResumeAction.CONTINUE: self.continue_jobs,
            ResumeAction.RETRY: self.retry_jobs,
            ResumeAction.MANUAL_REVIEW: self.manual_review,
        }
        return tuple(job.job_id for job in groups[action])


def build_resume_plan(jobs: Iterable[JobRecord]) -> ResumePlan:
    """Build a fail-closed, deterministic resume plan from local rows.

    Completed rows are never actionable.  Retry rows remain separate from
    unfinished rows so a future executor can apply T3-007 backoff before
    retrying them.  Permanent failures and quarantined files require a manual
    decision and are never automatically resumed.
    """

    groups: dict[ResumeAction, list[JobRecord]] = {
        ResumeAction.SKIP_COMPLETED: [],
        ResumeAction.CONTINUE: [],
        ResumeAction.RETRY: [],
        ResumeAction.MANUAL_REVIEW: [],
    }
    seen_job_ids: set[str] = set()
    known_statuses = set(STATUSES)

    for job in jobs:
        if job.job_id in seen_job_ids:
            raise ResumeValidationError(f"duplicate inventory job_id: {job.job_id}")
        seen_job_ids.add(job.job_id)
        if job.status not in known_statuses:
            raise ResumeValidationError(f"unknown inventory status: {job.status}")

        if job.status in COMPLETED_STATUSES:
            action = ResumeAction.SKIP_COMPLETED
        elif job.status in CONTINUE_STATUSES:
            action = ResumeAction.CONTINUE
        elif job.status in RETRY_STATUSES:
            action = ResumeAction.RETRY
        elif job.status in MANUAL_REVIEW_STATUSES:
            action = ResumeAction.MANUAL_REVIEW
        else:  # pragma: no cover - guarded by the explicit status sets above
            raise ResumeValidationError(f"unclassified inventory status: {job.status}")
        groups[action].append(job)

    return ResumePlan(
        skip_completed=tuple(sorted(groups[ResumeAction.SKIP_COMPLETED], key=lambda job: job.job_id)),
        continue_jobs=tuple(sorted(groups[ResumeAction.CONTINUE], key=lambda job: job.job_id)),
        retry_jobs=tuple(sorted(groups[ResumeAction.RETRY], key=lambda job: job.job_id)),
        manual_review=tuple(sorted(groups[ResumeAction.MANUAL_REVIEW], key=lambda job: job.job_id)),
    )


__all__ = [
    "COMPLETED_STATUSES",
    "CONTINUE_STATUSES",
    "MANUAL_REVIEW_STATUSES",
    "RETRY_STATUSES",
    "ResumeAction",
    "ResumePlan",
    "ResumeValidationError",
    "build_resume_plan",
]
