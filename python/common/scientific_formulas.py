"""Deterministic scalar/vector formulas approved by the PRD and Tahap 1.

Functions in this module operate on already validated finite values. They do
not read data, contact a service, write files, or choose scientific thresholds.
Missing values must be filtered by the caller and are never silently converted
to zero.
"""

from __future__ import annotations

import math
from typing import Iterable


class FormulaError(ValueError):
    """Raised when formula inputs are empty, mismatched, or non-finite."""


def _finite(value: float, label: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise FormulaError(f"{label} must be finite")
    return value


def _values(values: Iterable[float], label: str) -> tuple[float, ...]:
    result = tuple(_finite(value, label) for value in values)
    if not result:
        raise FormulaError(f"{label} must not be empty")
    return result


def speed(u: float, v: float) -> float:
    """Return scalar current speed ``sqrt(u**2 + v**2)`` in m/s."""

    return math.hypot(_finite(u, "u"), _finite(v, "v"))


def mean_speed(speeds: Iterable[float]) -> float:
    """Return the arithmetic mean of valid scalar speeds."""

    values = _values(speeds, "speeds")
    return math.fsum(values) / len(values)


def mean_components(
    u_values: Iterable[float], v_values: Iterable[float]
) -> tuple[float, float]:
    """Return pairwise means of zonal and meridional components."""

    u = _values(u_values, "u_values")
    v = _values(v_values, "v_values")
    if len(u) != len(v):
        raise FormulaError("u_values and v_values must have the same length")
    return math.fsum(u) / len(u), math.fsum(v) / len(v)


def resultant_speed(mean_u: float, mean_v: float) -> float:
    """Return ``sqrt(mean_u**2 + mean_v**2)`` in m/s."""

    return speed(mean_u, mean_v)


def resultant_direction(mean_u: float, mean_v: float) -> float | None:
    """Return toward-bearing degrees clockwise from north, or ``None`` at zero."""

    u = _finite(mean_u, "mean_u")
    v = _finite(mean_v, "mean_v")
    if u == 0.0 and v == 0.0:
        return None
    # atan2(x, y) gives a bearing from north, unlike the usual atan2(y, x).
    return math.degrees(math.atan2(u, v)) % 360.0


def persistence(resultant: float, average_speed: float) -> float | None:
    """Return ``resultant / average_speed``; return ``None`` for zero denominator."""

    resultant_value = _finite(resultant, "resultant")
    average_value = _finite(average_speed, "average_speed")
    if resultant_value < 0 or average_value < 0:
        raise FormulaError("speed values must be non-negative")
    if average_value == 0.0:
        return None
    return resultant_value / average_value


def vector_statistics(
    u_values: Iterable[float], v_values: Iterable[float]
) -> dict[str, float | int | None]:
    """Return the approved core vector statistics for paired valid observations."""

    u = _values(u_values, "u_values")
    v = _values(v_values, "v_values")
    if len(u) != len(v):
        raise FormulaError("u_values and v_values must have the same length")
    speeds = tuple(speed(u_value, v_value) for u_value, v_value in zip(u, v))
    average_u = math.fsum(u) / len(u)
    average_v = math.fsum(v) / len(v)
    average = mean_speed(speeds)
    resultant = resultant_speed(average_u, average_v)
    return {
        "count": len(u),
        "mean_speed": average,
        "mean_u": average_u,
        "mean_v": average_v,
        "resultant_speed": resultant,
        "resultant_direction": resultant_direction(average_u, average_v),
        "persistence_index": persistence(resultant, average),
    }
