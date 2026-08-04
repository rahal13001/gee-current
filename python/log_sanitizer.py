"""Offline sanitizer for Stage 3 download logs.

The sanitizer accepts caller-supplied text or structured events only.  It never
reads environment variables, credential files, network responses, or log
files.  Unknown object values are removed rather than serialized so an
exception representation cannot accidentally expose a credential-bearing
object.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import re
from typing import Any


SECRET_REDACTION = "<SECRET>"
TOKEN_REDACTION = "<TOKEN_REDACTED>"
EMAIL_REDACTION = "<EMAIL_REDACTED>"
USER_PATH_REDACTION = "<USER_PATH_REDACTED>"
OBJECT_REDACTION = "<OBJECT_REDACTED>"

_SENSITIVE_KEY_RE = re.compile(
    r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|"
    r"refresh[_-]?token|id[_-]?token|client[_-]?secret|private[_-]?key|"
    r"credential(?:s)?|authorization|proxy-authorization|cookie|set-cookie)"
)
_SENSITIVE_PAIR_RE = re.compile(
    r"(?i)(?P<prefix>\b(?:password|passwd|secret|api[_-]?key|"
    r"access[_-]?token|refresh[_-]?token|id[_-]?token|client[_-]?secret|"
    r"private[_-]?key|credential(?:s)?)\b\s*[:=]\s*)"
    r"(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^,\s;&}]+)"
)
_AUTH_HEADER_RE = re.compile(
    r"(?i)(?P<prefix>\b(?:authorization|proxy-authorization)\b\s*[:=]\s*)"
    r"(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|"
    r"(?:(?:Bearer|Basic)\s+[^,\s;&}]+|[^,\s;&}]+))"
)
_COOKIE_HEADER_RE = re.compile(
    r"(?i)(?P<prefix>\b(?:cookie|set-cookie)\b\s*[:=]\s*)"
    r"(?P<value>\"[^\"\r\n]*\"|'[^'\r\n]*'|[^,\r\n]+)"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_BASIC_RE = re.compile(r"(?i)\bBasic\s+[A-Za-z0-9+/=]+")
_SIGNED_QUERY_RE = re.compile(
    r"(?i)(?P<prefix>[?&](?:access_token|api_key|api-key|token|"
    r"signature|sig|x-amz-signature|x-amz-credential)=[^&#\s]+)"
)
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_USER_PATH_RE = re.compile(r"(?i)[A-Z]:[\\/]Users[\\/][^\s\"']+")


def _redact_sensitive_pair(match: re.Match[str]) -> str:
    return f"{match.group('prefix')}{SECRET_REDACTION}"


def _redact_auth_header(match: re.Match[str]) -> str:
    return f"{match.group('prefix')}{SECRET_REDACTION}"


def sanitize_text(value: str) -> str:
    """Redact sensitive values from one caller-supplied log message."""

    if not isinstance(value, str):
        raise TypeError("log text must be a string")
    sanitized = _SENSITIVE_PAIR_RE.sub(_redact_sensitive_pair, value)
    sanitized = _COOKIE_HEADER_RE.sub(_redact_auth_header, sanitized)
    sanitized = _AUTH_HEADER_RE.sub(_redact_auth_header, sanitized)
    sanitized = _BEARER_RE.sub(f"Bearer {TOKEN_REDACTION}", sanitized)
    sanitized = _BASIC_RE.sub(f"Basic {TOKEN_REDACTION}", sanitized)
    sanitized = _SIGNED_QUERY_RE.sub(
        lambda match: match.group("prefix").split("=", 1)[0] + f"={TOKEN_REDACTION}",
        sanitized,
    )
    sanitized = _EMAIL_RE.sub(EMAIL_REDACTION, sanitized)
    return _USER_PATH_RE.sub(USER_PATH_REDACTION, sanitized)


def _is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_RE.search(key))


def sanitize_event(value: Any) -> Any:
    """Recursively sanitize a JSON-like event without mutating its input."""

    if isinstance(value, Mapping):
        sanitized: dict[Any, Any] = {}
        for key, item in value.items():
            if isinstance(key, str) and _is_sensitive_key(key):
                sanitized[key] = SECRET_REDACTION
            else:
                sanitized[key] = sanitize_event(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_event(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_event(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return OBJECT_REDACTION


def render_event(event: Mapping[str, Any]) -> str:
    """Return deterministic JSON for a sanitized structured log event."""

    if not isinstance(event, Mapping):
        raise TypeError("log event must be a mapping")
    return json.dumps(
        sanitize_event(event),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sanitize_exception(error: BaseException) -> dict[str, str]:
    """Keep exception class and sanitized message, never a full traceback."""

    if not isinstance(error, BaseException):
        raise TypeError("error must be an exception")
    return {
        "exception_class": type(error).__name__,
        "message": sanitize_text(str(error)),
    }
