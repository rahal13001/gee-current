# REQUIREMENTS_TRACEABILITY.md

Baseline: 2026-08-03. Status follows the project vocabulary; `PASS` is not used here.
Evidence is local/offline unless explicitly stated otherwise. User-reported setup/runtime evidence is labeled as such and was not repeated by Codex.

## Foundation and skill requirements

| requirement_id | description | stage | implementation_file | test_file | status | evidence | notes |
|---|---|---|---|---|---|---|---|
| FND-001..FND-005 | Repository, root instructions, ignore rules, secret baseline, quality config | M0 | `AGENTS.md`, `.gitignore`, `pyproject.toml`, `tools/security/check_secrets.ps1` | `tools/run_foundation_checks.ps1` | TESTED | `outputs/evidence/foundation/` | offline only |
| FND-006 | Requirements and lock | M0 | `requirements.txt`, `requirements-lock.txt` | `outputs/evidence/foundation/FND-006_dependency_lock.result.txt` | PASS_WITH_NOTES | Approved local `.venv`; Python 3.12.13; 85 package versions recorded; `pip check` exit 0 | Clean-room reinstall was not run; no network or dependency installation |
| FND-007 | Setup and authentication boundary | M0 | `outputs/evidence/foundation/FND-007_setup_report.md` | — | PASS_WITH_NOTES | User reports `.venv`, `earthengine-api 1.7.37`, `copernicusmarine 2.4.1`, Copernicus login, Earth Engine OAuth, and `ee.Number(1).getInfo() = 1` for `ee-rahal13001` | Not rerun; no credential read; dependency lock is now recorded with notes |
| FND-008 | User-managed authentication and Codex boundary | M0 | `docs/SETUP_AND_AUTHENTICATION.md`, `docs/SECURITY_AND_SECRETS.md` | — | IMPLEMENTED | policy and evidence boundary | Codex did not authenticate or inspect credential contents |
| FND-009 | Noncommercial purpose, Project ID, and registration record | M0 | `outputs/evidence/foundation/FND-009_governance_record.md` | — | PASS_WITH_NOTES | User reports Project ID `ee-rahal13001` and noncommercial registration | Exact Earth Engine tier, billing, IAM, EECU, and asset root are not claimed or audited |
| FND-010 | Cloud/EECU monitoring plan and review | M0 | `outputs/evidence/foundation/FND-010_cost_monitoring_plan.md` | — | PASS_WITH_NOTES | User-managed review records EECU `0`, quota usage `0`, IAM `Owner`, no linked billing account, and 6-row resource inventory CSV | Exact tier, Resource Search scope/filter, and inventory completeness were not independently audited; no operational Cloud action was run |
| FND-011..FND-018 | Status, traceability, test registration, ADRs, changelog, checker, runner, evidence | M0 | `docs/IMPLEMENTATION_STATUS.md`, this file, `docs/adr/`, `CHANGELOG.md`, `tools/` | `tools/run_foundation_checks.ps1` | TESTED | local files/evidence | ADRs are PROPOSED |
| FND-019 | GitHub push protection/secret scanning review | M0 | `outputs/evidence/foundation/FND-019_github_security_review.md` | — | PASS_WITH_NOTES | local Git status/diff/secret-check evidence | GitHub push protection, secret scanning, ruleset, and branch protection remote belum diaudit |
| FND-020 | Active PRD and Stage 0–3 document baseline | M0 | `docs/` and `docs/audits/TOOLS_AND_SKILLS_INVENTORY.md` | — | PASS_WITH_NOTES | source register in audit | current repository uses `docs/` root; no duplicate copies |
| FND-SKILL-001 | Verifikasi Graphify | M0 | `graphify-out/`, `docs/audits/GRAPHIFY_FOUNDATION_AUDIT.md` | Graphify commands recorded in audit | TESTED | Graphify output and diagnostics | no external backend/network |
| FND-SKILL-002 | Verifikasi GEEMu | M0 | `docs/audits/TOOLS_AND_SKILLS_INVENTORY.md`, `GEEMU_FOUNDATION_RUN.md` | local import/reference check | TESTED_WITH_NOTES | skill/reference/template inventory and user-reported smoke | runtime smoke tidak diulang; exact tier, IAM, billing, EECU, asset root, dan AOI tidak diaudit |

## PRD functional and governance requirements

| requirement_id | description | stage | implementation_file | test_file | status | evidence | notes |
|---|---|---|---|---|---|---|---|
| FR-CONF-01 | AOI terpisah dari kode | T1 | `config/study_area.json`, `config/pilot_config.schema.json`, `python/common/config_loader.py` | `outputs/evidence/stage_1/T1_config_validation.result.txt` | PASS_WITH_NOTES | User-provided pilot bounding box recorded with `EPSG:4326` and `aoi_id=pilot_001`; 3 offline loader tests pass | Exact polygon provenance remains downstream work |
| FR-CONF-02 | Tanggal terpisah | T1 | `config/analysis_period.json`, `python/common/config_loader.py` | `outputs/evidence/stage_1/T1_config_validation.result.txt` | PASS_WITH_NOTES | 2015–2025 end-exclusive period and 132/993 expected counts recorded and validated | Runtime period tests remain offline-only |
| FR-CONF-03 | Kedalaman terkonfigurasi | T1 | `config/depth_selection.json`, `python/common/constants.py` | `outputs/evidence/stage_1/T1_config_validation.result.txt` | PASS_WITH_NOTES | `0.494025 m` and `1e-6 m` tolerance recorded and validated | Full 50-level extraction was not run |
| FR-CONF-04 | Threshold terkonfigurasi | T1 | `config/statistics.json`, `python/common/config_loader.py` | `outputs/evidence/stage_1/T1_config_validation.result.txt` | PASS_WITH_NOTES | Threshold list remains empty/TBD; no value was invented | Threshold decision remains open |
| FR-CONF-05 | Project ID/asset root | T1 | `config/local.example.json`, `config/asset_naming.json`, `python/common/config_loader.py` | `outputs/evidence/stage_1/T1_config_validation.result.txt` | PASS_WITH_NOTES | Project `ee-rahal13001` and user-created asset root recorded and prefix-validated | Asset existence/write access was user-reported and not independently verified |
| FR-CONF-06 | Tidak ada credential repo | M0 | `.gitignore`, `tools/security/check_secrets.ps1`, `tools/validate_m1_config.ps1` | `outputs/evidence/stage_1/T1_config_validation.result.txt` | TESTED | Config validation and repository secret scan suppress values | Checker is baseline, not full secret service |
| FR-META-01 | Describe produk/dataset | T0 | `docs/audits/COPERNICUS_METADATA_READONLY_CHECK.md` | TST-META-001..003 | PASS_WITH_NOTES | Prior read-only describe audit records matching product and dataset IDs | Not rerun in this session; no authentication or network |
| FR-META-02 | Snapshot JSON | T0 | `outputs/evidence/stage_0/metadata_snapshot_2026-08-02.json` | TST-META-004 | PASS_WITH_NOTES | Sanitized metadata snapshot recorded from prior audit | Raw response/checksum and immutable snapshot workflow remain downstream |
| FR-META-03 | Versi Toolbox | T0 | `outputs/evidence/foundation/FND-006_dependency_lock.result.txt` | TST-META-005 | PASS_WITH_NOTES | Approved environment records `copernicusmarine==2.4.1` | Runtime import/version was not rerun |
| FR-META-04 | Dataset version/part | T0 | `outputs/evidence/stage_0/metadata_snapshot_2026-08-02.json` | TST-META-006,010 | PASS_WITH_NOTES | Metadata version `202311` recorded; part explicitly marked not reported | Part remains unavailable in evidence |
| FR-META-05 | Stop on material metadata change | T0 | — | TST-META-007..009 | NOT_STARTED | — | Detector not implemented; no material-change claim |
| FR-DL-01 | 132 bulanan | T3 | — | TST-DL-001..002 | NOT_STARTED | — | no data/download |
| FR-DL-02 | 33 paket JFM | T3 | — | TST-DL-003..004 | NOT_STARTED | — | no data/download |
| FR-DL-03 | Retry | T3 | — | TST-DL-005..006 | NOT_STARTED | — | |
| FR-DL-04 | Resume | T3 | — | TST-DL-007..008 | NOT_STARTED | — | |
| FR-DL-05 | Inventory SQLite/CSV | T3 | — | TST-DL-009..010 | NOT_STARTED | — | |
| FR-DL-06 | SHA-256 | T3 | — | TST-DL-011..012 | NOT_STARTED | — | |
| FR-DL-07 | Karantina | T3 | — | TST-DL-013 | NOT_STARTED | — | |
| FR-DL-08 | Dry run | T3 | — | TST-DL-014 | NOT_STARTED | — | |
| FR-DL-09 | Daily full off | T3 | ADR-006 | TST-DL-015 | IMPLEMENTED | ADR-006 | implementation guard downstream |
| FR-VAL-01..FR-VAL-09 | Validasi variabel, unit, depth, time, mask, latitude, encoding, range, report | T4 | — | TST-VAL-001..020 | NOT_STARTED | — | downstream |
| FR-CONV-01..FR-CONV-07 | Float32, bands, mask, CRS, no resampling, time metadata, comparison | T5 | — | TST-CONV-001..014 | NOT_STARTED | — | downstream |
| FR-PY-01..FR-PY-17 | Analytics speed, vector, statistics, climatology, anomaly, trend, zonal, precompute | T5 | — | TST-PY-001..030 | NOT_STARTED | — | downstream |
| FR-GEE-01..FR-GEE-11 | Source collection, filter, light analysis, precompute readers, exports, metadata, limitations | T6–T9 | — | TST-GEE-001..020 | BLOCKED | — | no runtime/auth/assets |
| FR-VEC-01..FR-VEC-07 | Cardinal directions, arrows, sampling, legend, resolution honesty | T8 | — | TST-VEC-001..015 | NOT_STARTED | — | downstream |
| GOV-01 | Purpose nonkomersial | M0 | `FND-009_governance_record.md` | TST-GOV-001 | IMPLEMENTED | governance record | actual owner/date open |
| GOV-02 | Project ID khusus | M0 | `FND-009_governance_record.md` | TST-GOV-002 | PASS_WITH_NOTES | User reports `ee-rahal13001` | Project ID belum diaudit terhadap IAM, billing, asset root, atau penggunaan Cloud |
| GOV-03 | Registrasi nonkomersial | M0 | `FND-009_governance_record.md` | TST-GOV-003 | PASS_WITH_NOTES | User reports noncommercial registration | Exact tier dan tanggal verifikasi tidak diklaim; audit administratif tetap diperlukan |
| GOV-04 | EECU dipantau | M0 | `FND-010_cost_monitoring_plan.md` | TST-GOV-004 | PASS_WITH_NOTES | User-managed quota view records EECU usage `0` and active tasks `0` | No Codex authentication or operational computation; exact tier not inferred |
| GOV-05 | Cloud cost monitored | M0 | `FND-010_cost_monitoring_plan.md` | TST-GOV-005 | PASS_WITH_NOTES | User-managed billing view records no linked billing account | Billing state does not establish exact tier; no operational Cloud action was run |
| GOV-06 | Tidak operasional | M0 | `ADR-010-tidak-operasional.md` | TST-GOV-006 | IMPLEMENTED | proposed ADR/PRD | inherited decision |
| GOV-07 | Policy rechecked at deployment | M0/T9 | `ADR-003-nonkomersial.md` | TST-GOV-007 | IMPLEMENTED | proposed ADR | release gate remains |

## Source of truth register

The active document paths are the files currently present under `docs/`; the active repository uses the current `docs/` root layout.
Stage 0–3 documents, ADRs, status, and traceability are registered above. Foundation artifacts and audit reports are local evidence.
Stage 0–3 documents remain normative inputs; user-reported runtime/setup facts are not independent Cloud or credential audits.

Current reconciliation note: Foundation artifacts and audit reports are local evidence; user-reported runtime/setup facts are not independent Cloud or credential audits.

## Explicit ID coverage index

The following IDs are explicitly covered by this traceability baseline:

```text
FND-001 FND-002 FND-003 FND-004 FND-005 FND-006 FND-007 FND-008 FND-009 FND-010 FND-011 FND-012 FND-013 FND-014 FND-015 FND-016 FND-017 FND-018 FND-019 FND-020 FND-SKILL-001 FND-SKILL-002
FR-CONF-01 FR-CONF-02 FR-CONF-03 FR-CONF-04 FR-CONF-05 FR-CONF-06
FR-META-01 FR-META-02 FR-META-03 FR-META-04 FR-META-05
FR-DL-01 FR-DL-02 FR-DL-03 FR-DL-04 FR-DL-05 FR-DL-06 FR-DL-07 FR-DL-08 FR-DL-09
FR-VAL-01 FR-VAL-02 FR-VAL-03 FR-VAL-04 FR-VAL-05 FR-VAL-06 FR-VAL-07 FR-VAL-08 FR-VAL-09
FR-CONV-01 FR-CONV-02 FR-CONV-03 FR-CONV-04 FR-CONV-05 FR-CONV-06 FR-CONV-07
FR-PY-01 FR-PY-02 FR-PY-03 FR-PY-04 FR-PY-05 FR-PY-06 FR-PY-07 FR-PY-08 FR-PY-09 FR-PY-10 FR-PY-11 FR-PY-12 FR-PY-13 FR-PY-14 FR-PY-15 FR-PY-16 FR-PY-17
FR-GEE-01 FR-GEE-02 FR-GEE-03 FR-GEE-04 FR-GEE-05 FR-GEE-06 FR-GEE-07 FR-GEE-08 FR-GEE-09 FR-GEE-10 FR-GEE-11
FR-VEC-01 FR-VEC-02 FR-VEC-03 FR-VEC-04 FR-VEC-05 FR-VEC-06 FR-VEC-07
GOV-01 GOV-02 GOV-03 GOV-04 GOV-05 GOV-06 GOV-07
```
