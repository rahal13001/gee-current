# FND-007 Setup Report

- Status: `PASS_WITH_NOTES`
- Scope: setup/authentication evidence is reconciled from the user's report; Codex did not repeat login,
  OAuth, credential checks, or online initialization.

## User-reported evidence

- Local `.venv` is available.
- `earthengine-api` version `1.7.37` is installed.
- `copernicusmarine` version `2.4.1` is installed.
- Copernicus Marine login has been completed by the user.
- Earth Engine OAuth has been completed by the user and the Earth Engine API is active.
- User-reported smoke test: `ee.Initialize(project='ee-rahal13001')` followed by
  `ee.Number(1).getInfo()` returned `1` (reported exit status 0).
- Read-only metadata evidence is recorded in
  `docs/audits/COPERNICUS_METADATA_READONLY_CHECK.md`.

## Limitations and next action

- This is not an independent credential, IAM, billing, EECU, exact-tier, asset-root, or AOI audit.
- No credential/token contents were read, displayed, or copied.
- FND-006 remains `BLOCKED` until an approved reproducible dependency lock is created.
- Tahap 2 remains pending its approved AOI, original-data pilot, and all required validation evidence.
