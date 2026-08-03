# Data Dictionary Baseline

This is the Tahap 1 offline data dictionary baseline. It records approved
identifiers and meanings without claiming that raw data files or Earth Engine
assets have been created.

| Field | Value | Evidence/limit |
|---|---|---|
| Product ID | `GLOBAL_MULTIYEAR_PHY_001_030` | Copernicus read-only metadata audit |
| Daily dataset | `cmems_mod_glo_phy_my_0.083deg_P1D-m` | Copernicus read-only metadata audit |
| Monthly dataset | `cmems_mod_glo_phy_my_0.083deg_P1M-m` | Copernicus read-only metadata audit |
| Zonal current | `uo` | Unit `m s-1` |
| Meridional current | `vo` | Unit `m s-1` |
| Analysis depth | `0.494025 m` | Tolerance `1e-6 m`; full 50 levels not extracted |
| Project period | `2015-01-01` to `2026-01-01` exclusive | 132 monthly; 993 daily JFM expected |
| Pilot AOI | `pilot_001` bbox | User-provided; exact polygon not provided |
| Direction convention | towards, clockwise from north | Existing Tahap 1 decision |
| Speed thresholds | empty / `TBD` | No scientific threshold invented |
| Earth Engine asset root | `projects/ee-rahal13001/assets/glorys_current` | User-reported; not verified by Codex |

Mask, nodata, raw encoding, and numerical data ranges remain validation inputs
for the approved Tahap 2 pilot and are not asserted here.
