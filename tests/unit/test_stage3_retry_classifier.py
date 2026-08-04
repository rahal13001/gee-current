from __future__ import annotations

import unittest

from python.retry_classifier import (
    PERMANENT,
    RETRYABLE,
    RetryDecision,
    classify_error,
    is_permanent,
    is_retryable,
)


class _ResponseError(Exception):
    def __init__(self, status_code: int):
        super().__init__(f"HTTP response {status_code}")
        self.status_code = status_code


class Stage3RetryClassifierTests(unittest.TestCase):
    def test_public_decisions_are_stable_strings(self) -> None:
        self.assertEqual(RetryDecision.RETRYABLE.value, "retryable")
        self.assertEqual(RetryDecision.PERMANENT.value, "permanent")
        self.assertEqual(RETRYABLE, RetryDecision.RETRYABLE)
        self.assertEqual(PERMANENT, RetryDecision.PERMANENT)

    def test_transient_exception_types_are_retryable(self) -> None:
        for error in (
            TimeoutError("request timed out"),
            ConnectionError("connection lost"),
            ConnectionResetError("connection reset by peer"),
        ):
            with self.subTest(error=type(error).__name__):
                self.assertIs(classify_error(error), RetryDecision.RETRYABLE)

    def test_transient_messages_are_retryable(self) -> None:
        for message in (
            "temporary DNS failure in name resolution",
            "service temporarily unavailable",
            "partial file received",
            "dataset is currently being updated",
            "HTTP 503 service unavailable",
        ):
            with self.subTest(message=message):
                self.assertIs(classify_error(message), RetryDecision.RETRYABLE)

    def test_http_status_attribute_and_explicit_status(self) -> None:
        for error in (_ResponseError(500), "rate limited"):
            status = None if isinstance(error, _ResponseError) else 429
            with self.subTest(error=error):
                self.assertIs(
                    classify_error(error, http_status=status),
                    RetryDecision.RETRYABLE,
                )

        for status in (400, 401, 403, 404):
            with self.subTest(status=status):
                self.assertIs(
                    classify_error("request rejected", http_status=status),
                    RetryDecision.PERMANENT,
                )

    def test_normative_permanent_examples_are_not_retried(self) -> None:
        messages = (
            "wrong Dataset ID",
            "variable absent from dataset",
            "AOI outside dataset bounds",
            "wrong date supplied",
            "invalid credentials",
            "wrong depth configuration",
            "unsupported format",
        )
        for message in messages:
            with self.subTest(message=message):
                self.assertIs(classify_error(message), RetryDecision.PERMANENT)

    def test_unknown_error_fails_closed(self) -> None:
        self.assertIs(classify_error("unclassified local failure"), RetryDecision.PERMANENT)

    def test_boolean_helpers_match_decision(self) -> None:
        self.assertTrue(is_retryable(TimeoutError("timeout")))
        self.assertFalse(is_permanent(TimeoutError("timeout")))
        self.assertTrue(is_permanent("invalid Dataset ID"))
        self.assertFalse(is_retryable("invalid Dataset ID"))


if __name__ == "__main__":
    unittest.main()
