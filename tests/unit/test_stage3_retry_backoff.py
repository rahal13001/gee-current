from __future__ import annotations

import unittest

from python.retry_backoff import (
    BackoffPolicy,
    BackoffValidationError,
    DEFAULT_BACKOFF_POLICY,
    RetryLimitExceeded,
    calculate_backoff,
)


class Stage3RetryBackoffTests(unittest.TestCase):
    def test_default_policy_matches_stage3_schedule(self) -> None:
        self.assertEqual(
            [DEFAULT_BACKOFF_POLICY.delay_for_attempt(i) for i in range(1, 5)],
            [10.0, 30.0, 90.0, 270.0],
        )

    def test_formula_is_capped_by_maximum(self) -> None:
        policy = BackoffPolicy(
            initial_delay_seconds=10,
            multiplier=3,
            maximum_delay_seconds=50,
            max_attempts=6,
        )
        self.assertEqual(
            [policy.delay_for_attempt(i) for i in range(1, 7)],
            [10, 30, 50, 50, 50, 50],
        )

    def test_large_multiplier_is_capped_without_overflow(self) -> None:
        policy = BackoffPolicy(
            initial_delay_seconds=10,
            multiplier=1e308,
            maximum_delay_seconds=270,
            max_attempts=4,
        )
        self.assertEqual(policy.delay_for_attempt(4), 270.0)

    def test_attempt_limit_is_bounded(self) -> None:
        policy = BackoffPolicy(max_attempts=4)
        self.assertTrue(policy.can_retry(0))
        self.assertTrue(policy.can_retry(3))
        self.assertFalse(policy.can_retry(4))
        with self.assertRaises(RetryLimitExceeded):
            policy.delay_for_attempt(5)

    def test_function_uses_explicit_policy_values(self) -> None:
        self.assertEqual(
            calculate_backoff(
                3,
                initial_delay_seconds=2,
                multiplier=4,
                maximum_delay_seconds=20,
                max_attempts=3,
            ),
            20,
        )

    def test_invalid_policy_is_rejected(self) -> None:
        invalid_policies = (
            {"initial_delay_seconds": 0},
            {"multiplier": 0.5},
            {"maximum_delay_seconds": 5},
            {"max_attempts": 0},
        )
        for values in invalid_policies:
            with self.subTest(values=values):
                with self.assertRaises(BackoffValidationError):
                    BackoffPolicy(**values)

    def test_invalid_attempt_numbers_are_rejected(self) -> None:
        policy = BackoffPolicy()
        for attempt in (0, -1, True, 1.5):
            with self.subTest(attempt=attempt):
                with self.assertRaises(BackoffValidationError):
                    policy.delay_for_attempt(attempt)
        with self.assertRaises(BackoffValidationError):
            policy.can_retry(-1)


if __name__ == "__main__":
    unittest.main()
