# FND-007 Setup Report

- Status: `BLOCKED`
- Reason: setup/authentication requires approved dependency installation, user-managed Copernicus login,
  Earth Engine Project ID, and user-managed OAuth. None may be guessed or executed in this session.
- Offline evidence: repository files, pyproject config, GEEMu references, and no-runtime-import result are recorded in `docs/audits/TOOLS_AND_SKILLS_INVENTORY.md`.
- Required next action: user provides approval and runs official setup/authentication flows; Codex must not read credential contents.
