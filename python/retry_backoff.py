"""Offline exponential backoff policy for Stage 3 job retries.

This module calculates delays only.  It never sleeps, performs network I/O,
reads credentials, or executes a download.  The default policy follows the
Stage 3 job-level example: 10, 30, 90, and 270 seconds for four attempts.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


class BackoffValidationError(ValueError):
    """Raised when a backoff policy or attempt number is invalid."""


class RetryLimitExceeded(BackoffValidationError):
    """Raised when a caller requests a delay beyond the attempt limit."""


@dataclass(frozen=True)
class BackoffPolicy:
    """Validated, side-effect-free policy for retry delay calculation."""

    initial_delay_seconds: float = 10.0
    multiplier: float = 3.0
    maximum_delay_seconds: float = 270.0
    max_attempts: int = 4

    def __post_init__(self) -> None:
        for name, value in (
            ("initial_delay_seconds", self.initial_delay_seconds),
            ("multiplier", self.multiplier),
            ("maximum_delay_seconds", self.maximum_delay_seconds),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise BackoffValidationError(f"{name} must be numeric")
            if not math.isfinite(float(value)) or float(value) <= 0:
                raise BackoffValidationError(f"{name} must be finite and positive")
        if self.multiplier < 1:
            raise BackoffValidationError("multiplier must be at least 1")
        if self.maximum_delay_seconds < self.initial_delay_seconds:
            raise BackoffValidationError(
                "maximum_delay_seconds cannot be less than initial_delay_seconds"
            )
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or self.max_attempts < 1
        ):
            raise BackoffValidationError("max_attempts must be a positive integer")

    def can_retry(self, attempts_completed: int) -> bool:
        """Return whether another attempt is allowed.

        ``attempts_completed`` is a zero-based count from inventory/executor
        state: zero means no attempt has completed yet.
        """

        if isinstance(attempts_completed, bool) or not isinstance(attempts_completed, int):
            raise BackoffValidationError("attempts_completed must be an integer")
        if attempts_completed < 0:
            raise BackoffValidationError("attempts_completed cannot be negative")
        return attempts_completed < self.max_attempts

    def delay_for_attempt(self, attempt_number: int) -> float:
        """Return the capped delay for a one-based, allowed attempt number."""

        if isinstance(attempt_number, bool) or not isinstance(attempt_number, int):
            raise BackoffValidationError("attempt_number must be an integer")
        if attempt_number < 1:
            raise BackoffValidationError("attempt_number must be positive")
        if attempt_number > self.max_attempts:
            raise RetryLimitExceeded(
                f"attempt {attempt_number} exceeds max_attempts={self.max_attempts}"
            )
        delay = float(self.initial_delay_seconds)
        for _ in range(attempt_number - 1):
            if delay >= self.maximum_delay_seconds:
                return float(self.maximum_delay_seconds)
            delay = min(delay * float(self.multiplier), self.maximum_delay_seconds)
        return delay


DEFAULT_BACKOFF_POLICY = BackoffPolicy()


def calculate_backoff(
    attempt_number: int,
    *,
    initial_delay_seconds: float = 10.0,
    multiplier: float = 3.0,
    maximum_delay_seconds: float = 270.0,
    max_attempts: int = 4,
) -> float:
    """Calculate one delay using an explicit, validated policy."""

    policy = BackoffPolicy(
        initial_delay_seconds=initial_delay_seconds,
        multiplier=multiplier,
        maximum_delay_seconds=maximum_delay_seconds,
        max_attempts=max_attempts,
    )
    return policy.delay_for_attempt(attempt_number)


__all__ = [
    "BackoffPolicy",
    "BackoffValidationError",
    "DEFAULT_BACKOFF_POLICY",
    "RetryLimitExceeded",
    "calculate_backoff",
]
