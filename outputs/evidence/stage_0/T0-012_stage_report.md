# Tahap 0 Metadata Baseline Report

- Test ID: `T0-012`
- Status: `PASS_WITH_NOTES`
- Evidence date: `2026-08-03` (Asia/Jayapura)
- Source: `docs/audits/COPERNICUS_METADATA_READONLY_CHECK.md`
- Snapshot: `outputs/evidence/stage_0/metadata_snapshot_2026-08-03.json`

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
- Full active depth list: 50 levels, descending positive-down order, top model layer `0.49402499198913574 m`

## Decision and limitations

The metadata baseline is accepted with notes. User-managed product, daily, and
monthly describe results, the real 50-level extraction, and the sanitized
baseline-to-follow-up material-change comparison are recorded. The depth
validator accepts both ascending and descending monotonic coordinate order and
uses the shallowest positive-down value for the top-layer check. Raw NetCDF
validation, checksums, download, subset, upload, authentication, network, and
Cloud operations were not performed by Codex.

## Offline evidence added

- `outputs/evidence/stage_0/T0_describe_wrapper.plan.result.txt`
- `outputs/evidence/stage_0/T0_depth_validator.result.txt`
- `outputs/evidence/stage_0/T0_metadata_guard.result.txt`
- `outputs/evidence/stage_0/metadata_snapshot_2026-08-03.json`
- `outputs/evidence/stage_0/research_purpose_metadata.json`
