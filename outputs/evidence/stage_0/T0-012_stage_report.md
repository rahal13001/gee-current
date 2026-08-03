# Tahap 0 Metadata Baseline Report

- Test ID: `T0-012`
- Status: `IN_PROGRESS`
- Evidence date: `2026-08-02` (Asia/Jayapura)
- Source: `docs/audits/COPERNICUS_METADATA_READONLY_CHECK.md`
- Snapshot: `outputs/evidence/stage_0/metadata_snapshot_2026-08-02.json`

## Verified baseline

- Product: `GLOBAL_MULTIYEAR_PHY_001_030`
- Daily dataset: `cmems_mod_glo_phy_my_0.083deg_P1D-m`
- Monthly dataset: `cmems_mod_glo_phy_my_0.083deg_P1M-m`
- Variables: `uo`, `vo`
- Units: `m s-1`
- Selected depth: `0.494025 m` within `1e-6 m` tolerance
- Metadata version: `202311`
- Project period: `2015-01-01` inclusive to `2026-01-01` exclusive
- Expected project counts: 132 monthly and 993 daily JFM timesteps

## Decision and limitations

The metadata baseline is accepted with notes for configuration work, but the
Tahap 0 stage gate remains `IN_PROGRESS`. Full 50-level extraction, raw NetCDF
validation, checksums, and material-change detection were not run. No download,
subset, upload, or Cloud operation was performed in this session.
