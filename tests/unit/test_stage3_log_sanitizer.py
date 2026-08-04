from __future__ import annotations

import copy
import unittest

from python.log_sanitizer import (
    EMAIL_REDACTION,
    SECRET_REDACTION,
    TOKEN_REDACTION,
    USER_PATH_REDACTION,
    render_event,
    sanitize_event,
    sanitize_exception,
    sanitize_text,
)


class Stage3LogSanitizerTests(unittest.TestCase):
    def test_sensitive_pairs_and_auth_values_are_redacted(self) -> None:
        secret_value = "alpha" + "-synthetic"
        token_value = "token" + "-synthetic"
        bearer_value = "bearer" + "-synthetic"
        cookie_value = "cookie" + "-synthetic"
        message = (
            "password: "
            + secret_value
            + " access_token="
            + token_value
            + ", Authorization: Bearer "
            + bearer_value
            + ", Cookie: session="
            + cookie_value
            + "; other=also-sensitive, Basic dGVzdA=="
        )
        sanitized = sanitize_text(message)
        self.assertNotIn(secret_value, sanitized)
        self.assertNotIn(token_value, sanitized)
        self.assertNotIn(bearer_value, sanitized)
        self.assertNotIn(cookie_value, sanitized)
        self.assertIn(SECRET_REDACTION, sanitized)
        self.assertIn("Authorization: " + SECRET_REDACTION, sanitized)
        self.assertIn(f"Basic {TOKEN_REDACTION}", sanitized)

    def test_signed_query_values_are_redacted(self) -> None:
        signed_url = "https://example.invalid/file?token=opaque-token&x=kept"
        sanitized = sanitize_text(signed_url)
        self.assertNotIn("opaque-token", sanitized)
        self.assertIn("token=" + TOKEN_REDACTION, sanitized)
        self.assertIn("x=kept", sanitized)

    def test_email_and_user_profile_path_are_redacted(self) -> None:
        message = r"operator=tester@example.invalid path=C:\Users\sample\secret.log"
        sanitized = sanitize_text(message)
        self.assertNotIn("tester@example.invalid", sanitized)
        self.assertNotIn(r"C:\Users\sample\secret.log", sanitized)
        self.assertIn(EMAIL_REDACTION, sanitized)
        self.assertIn(USER_PATH_REDACTION, sanitized)

    def test_structured_event_redacts_nested_sensitive_fields_without_mutation(self) -> None:
        secret_value = "nested" + "-synthetic"
        event = {
            "job_id": "daily_jfm_2020_02",
            "status": "failed_retryable",
            "request": {"headers": {"Authorization": "Bearer opaque-value"}},
            "password": secret_value,
            "attempt": 1,
            "tags": ("download", "offline"),
        }
        original = copy.deepcopy(event)
        sanitized = sanitize_event(event)
        self.assertEqual(event, original)
        self.assertEqual(sanitized["password"], SECRET_REDACTION)
        self.assertEqual(sanitized["request"]["headers"]["Authorization"], SECRET_REDACTION)
        self.assertEqual(sanitized["job_id"], "daily_jfm_2020_02")
        self.assertEqual(sanitized["tags"], ["download", "offline"])
        self.assertNotIn(secret_value, render_event(event))

    def test_unknown_object_is_not_serialized(self) -> None:
        class CredentialLikeObject:
            def __repr__(self) -> str:
                return "CredentialLikeObject(opaque-value)"

        sanitized = sanitize_event({"response": CredentialLikeObject()})
        self.assertEqual(sanitized["response"], "<OBJECT_REDACTED>")

    def test_exception_keeps_class_but_sanitizes_message(self) -> None:
        secret_value = "exception" + "-synthetic"
        error = RuntimeError("request failed password=" + secret_value)
        sanitized = sanitize_exception(error)
        self.assertEqual(sanitized["exception_class"], "RuntimeError")
        self.assertNotIn(secret_value, sanitized["message"])
        self.assertIn(SECRET_REDACTION, sanitized["message"])

    def test_invalid_text_and_event_types_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            sanitize_text(123)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            render_event([])  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
