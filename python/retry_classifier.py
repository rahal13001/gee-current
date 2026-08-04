"""Offline retry classification for the Stage 3 download state machine.

The classifier is deliberately side-effect free.  It does not make requests,
inspect credentials, read files, or start a download.  Unknown errors fail
closed as ``permanent`` so a future executor cannot retry an unclassified
condition indefinitely.
"""

from __future__ import annotations

from enum import Enum
import errno
import re
import socket
from typing import Any


class RetryDecision(str, Enum):
    """The two decisions permitted by the Stage 3 retry policy."""

    RETRYABLE = "retryable"
    PERMANENT = "permanent"


RETRYABLE = RetryDecision.RETRYABLE
PERMANENT = RetryDecision.PERMANENT


_HTTP_STATUS_PATTERN = re.compile(r"\b(?:http(?:\s+status|\s+error)?\s*)?([45]\d{2})\b")

_PERMANENT_PATTERNS = (
    re.compile(r"\b(?:invalid|wrong|unknown)\s+dataset\s+id\b"),
    re.compile(r"\bdataset\s+id\b.*\b(?:invalid|wrong|unknown|missing|not found)\b"),
    re.compile(r"\b(?:unknown|invalid)\s+dataset\b"),
    re.compile(r"\bdataset\b.*\bnot found\b"),
    re.compile(r"\b(?:missing|absent|unknown|invalid)\s+variable\b"),
    re.compile(r"\bvariable\b.*\b(?:missing|absent|unknown|not found)\b"),
    re.compile(r"\b(?:aoi|area of interest|region)\b.*\b(?:outside|out of|beyond)\b.*\b(?:bound|range|coverage)\b"),
    re.compile(r"\b(?:outside|out of|beyond)\b.*\b(?:bounds|range|coverage)\b"),
    re.compile(r"\b(?:invalid|wrong|incorrect|unsupported)\s+(?:date|datetime|time)\b"),
    re.compile(r"\b(?:date|datetime|time)\b.*\b(?:invalid|wrong|incorrect|outside|not found)\b"),
    re.compile(r"\binvalid\s+credentials?\b"),
    re.compile(r"\b(?:authentication|authorization)\s+failed\b"),
    re.compile(r"\bunauthori[sz]ed\b"),
    re.compile(r"\bforbidden\b"),
    re.compile(r"\bpermission denied\b"),
    re.compile(r"\b(?:invalid|wrong|unsupported|mismatched?)\s+depth\b"),
    re.compile(r"\bdepth\b.*\b(?:invalid|wrong|unsupported|mismatch)\b"),
    re.compile(r"\bunsupported\s+format\b"),
    re.compile(r"\bformat\b.*\bnot supported\b"),
)

_RETRYABLE_PATTERNS = (
    re.compile(r"\btime(?:out|d out)\b"),
    re.compile(r"\bconnection\s+(?:reset|aborted|lost|closed|refused|error)\b"),
    re.compile(r"\btemporary\s+(?:dns|failure|network|error|unavailable)\b"),
    re.compile(r"\b(?:dns|name resolution)\b.*\b(?:temporary|failure|again)\b"),
    re.compile(r"\bservice\b.*\btemporar(?:y|ily)\b.*\bunavailable\b"),
    re.compile(r"\btemporarily\s+unavailable\b"),
    re.compile(r"\bpartial(?:ly)?\s+(?:downloaded|file)\b"),
    re.compile(r"\bincomplete\s+(?:file|download)\b"),
    re.compile(r"\bdataset\b.*\b(?:being|currently)\s+updated\b"),
    re.compile(r"\btry again\b"),
    re.compile(r"\b(?:http|status(?:\s+code)?)\s*5\d{2}\b"),
)

_TRANSIENT_EXCEPTION_TYPES = (
    TimeoutError,
    socket.timeout,
    ConnectionError,
    ConnectionResetError,
    ConnectionAbortedError,
    BrokenPipeError,
)

_TRANSIENT_ERRNOS = frozenset(
    {
        errno.ETIMEDOUT,
        errno.ECONNRESET,
        errno.ECONNABORTED,
        errno.EPIPE,
        getattr(errno, "EAI_AGAIN", -1),
    }
)


def _error_text(error: BaseException | str) -> str:
    """Return bounded, non-representational text for pattern matching."""

    if isinstance(error, BaseException):
        parts = [error.__class__.__name__, str(error)]
        cause = error.__cause__
        if cause is not None:
            parts.extend((cause.__class__.__name__, str(cause)))
        return " ".join(parts).lower()
    return str(error).lower()


def _status_from_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        status = int(value)
    except (TypeError, ValueError):
        return None
    return status if 100 <= status <= 599 else None


def _http_status(error: BaseException | str, explicit_status: int | None) -> int | None:
    status = _status_from_value(explicit_status)
    if status is not None:
        return status
    if isinstance(error, BaseException):
        for attribute in ("status_code", "status"):
            try:
                status = _status_from_value(getattr(error, attribute, None))
            except Exception:
                status = None
            if status is not None:
                return status
        try:
            response = getattr(error, "response", None)
            status = _status_from_value(getattr(response, "status_code", None))
        except Exception:
            status = None
        if status is not None:
            return status
    return None


def _message_status(text: str) -> int | None:
    match = _HTTP_STATUS_PATTERN.search(text)
    if match is None:
        return None
    return _status_from_value(match.group(1))


def _has_permanent_marker(text: str) -> bool:
    return any(pattern.search(text) for pattern in _PERMANENT_PATTERNS)


def _has_retryable_marker(text: str) -> bool:
    return any(pattern.search(text) for pattern in _RETRYABLE_PATTERNS)


def classify_error(
    error: BaseException | str,
    *,
    http_status: int | None = None,
) -> RetryDecision:
    """Classify one local error as ``retryable`` or ``permanent``.

    HTTP 408, 429, and 5xx responses are retryable.  Other 4xx responses are
    permanent.  Explicit HTTP status and permanent markers take precedence
    over exception classes and generic message markers.  Any unrecognized
    condition is permanent.
    """

    text = _error_text(error)
    status = _http_status(error, http_status) or _message_status(text)

    if status is not None:
        if status in (408, 429) or 500 <= status <= 599:
            return RetryDecision.RETRYABLE
        if 400 <= status <= 499:
            return RetryDecision.PERMANENT

    if _has_permanent_marker(text):
        return RetryDecision.PERMANENT

    if isinstance(error, PermissionError):
        return RetryDecision.PERMANENT

    if isinstance(error, _TRANSIENT_EXCEPTION_TYPES):
        return RetryDecision.RETRYABLE

    if isinstance(error, OSError) and getattr(error, "errno", None) in _TRANSIENT_ERRNOS:
        return RetryDecision.RETRYABLE

    if _has_retryable_marker(text):
        return RetryDecision.RETRYABLE

    return RetryDecision.PERMANENT


def is_retryable(error: BaseException | str, *, http_status: int | None = None) -> bool:
    """Return whether the error may be retried by a future executor."""

    return classify_error(error, http_status=http_status) is RetryDecision.RETRYABLE


def is_permanent(error: BaseException | str, *, http_status: int | None = None) -> bool:
    """Return whether the error must stop without an automatic retry."""

    return classify_error(error, http_status=http_status) is RetryDecision.PERMANENT


__all__ = [
    "PERMANENT",
    "RETRYABLE",
    "RetryDecision",
    "classify_error",
    "is_permanent",
    "is_retryable",
]
