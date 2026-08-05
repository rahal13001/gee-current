# Approved methodology formulas

This file is an implementation register for the formulas approved in the PRD,
Tahap 1, and ADR-011. It does not introduce safety thresholds or alter the
direction convention. Local Stage 5 processing is evidenced separately; no
GEE/cloud processing is claimed here.

Implementation: `python/common/scientific_formulas.py`

| Output | Definition | Convention |
|---|---|---|
| `speed` | `sqrt(u² + v²)` | m/s |
| `mean_speed` | arithmetic mean of scalar speeds | valid observations only |
| `mean_u`, `mean_v` | arithmetic mean of paired components | valid observations only |
| `resultant_speed` | `sqrt(mean_u² + mean_v²)` | m/s |
| `resultant_direction` | `atan2(mean_u, mean_v)` converted to degrees modulo 360 | toward, clockwise from north |
| `persistence_index` | `resultant_speed / mean_speed` | `None`/NoData when `mean_speed = 0` |

The implementation fails closed for empty, mismatched, or non-finite inputs.
It does not replace NetCDF validation, masking, or the Tahap 2 pilot.
