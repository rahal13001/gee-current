# Tools and Skills Inventory — Foundation/M0

Tanggal audit: 2026-08-03 (Asia/Jayapura)

## Scope dan batas

Pemeriksaan ini read-only dan offline untuk aktivitas Codex. Tidak ada login ulang, credential file read,
Earth Engine initialization ulang, Copernicus access ulang, network, install/upgrade, download, upload,
atau operasi Git destruktif. Review IAM, billing, EECU, dan resource dilakukan user-managed dan dicatat
sebagai evidence terpisah; Codex tidak menjalankan operasi Cloud atau mengaudit kelengkapannya.

## Graphify

| Item | Evidence | Result |
|---|---|---|
| Skill | `C:\Users\loka_\.codex\skills\graphify\SKILL.md` dibaca | AVAILABLE |
| Local executable | `C:\Users\loka_\.local\bin\graphify.exe` | AVAILABLE |
| Help | `graphify --help` | AVAILABLE; command `extract`, `cluster-only`, `diagnose`, `god-nodes`, `query` terdokumentasi |
| Offline extraction | `graphify extract . --code-only --no-cluster --out .` | EXECUTED; 0 code, 11 docs skipped, graph kosong by design |
| Semantic audit | sub-agent Graphify extraction + local graph processing | EVIDENCE in `graphify-out/` and audit report |

## GEEMu

| Item | Evidence | Result |
|---|---|---|
| Skill | `C:\Users\loka_\.codex\skills\GEEMu\SKILL.md` dibaca | AVAILABLE |
| Required references | `references/local_environment.md`, `data_layer.md`, `research_design.md` | AVAILABLE dan dibaca |
| Templates | `templates/RUN.md`, `templates/DATA_LAYER.md` | AVAILABLE dan dibaca |
| Local examples | `examples/geemap_local_download/RUN.md`, `DATA_LAYER.md` | AVAILABLE dan dibaca |
| Local runtime | user reports `.venv`, `earthengine-api 1.7.37`, `copernicusmarine 2.4.1` | USER-REPORTED AVAILABLE |
| EE initialization/auth | user reports OAuth selesai, API aktif, `ee.Initialize(project='ee-rahal13001')`; `ee.Number(1).getInfo()` menghasilkan `1` | USER-REPORTED SMOKE PASS; tidak diulang |
| Copernicus login/metadata | user reports login selesai; metadata read-only audit tersedia | USER-REPORTED / `COPERNICUS_METADATA_READONLY_CHECK.md` |
| Workflow readiness | pola RUN/DATA_LAYER dipetakan; AOI bbox dan asset root tercatat; FND-010 | PARTIAL; AOI/asset root dan review Cloud user-managed tersedia, tetapi exact tier, kelengkapan inventory, dan write access tidak diaudit independen |

## Dependency Earth Engine yang kelak diperlukan

`earthengine-api` (`ee`) dan dependency Python lain yang akan dikunci setelah environment dan approval tersedia.
`geemap`/`geopandas` tidak diklaim terpasang dari evidence user yang tersedia. Tidak ada paket yang dipasang sesi ini.

## Kesimpulan skill gate

- FND-SKILL-001: `TESTED` pada availability/help/offline invocation; semantic graph evidence tersedia.
- FND-SKILL-002: `TESTED_WITH_NOTES` pada skill/reference/template completeness dan user-reported runtime smoke;
  AOI/asset root serta user-managed Cloud review tersedia, tetapi exact tier, kelengkapan inventory,
  dan write access tetap tidak diaudit independen.

## Post-T2/T3 inventory refresh

- AOI bbox, asset root, IAM `Owner`, billing tanpa billing account, EECU `0`, quota `0`, dan resource review
  tersedia sebagai evidence user-managed; tidak ada operasi Cloud Codex yang diulang.
- T2 corrected assets, display helper, T3 plan builder, dan unit tests tersedia di repository.
- T3-004 inventory SQLite schema/state machine dan unit tests tersedia; Graphify code-only refresh terakhir mencatat 372 node, 496 edge, 49 komunitas, dan diagnostics bersih.
- T3-005 CSV export dan unit test konsistensi SQLite-CSV tersedia; refresh Graphify terakhir mencatat 375 node, 503 edge, 51 komunitas, dan diagnostics bersih.
- T3-006 retry classifier dan unit tests offline tersedia; unknown error fail-closed ke `permanent`. Executor/backoff/download belum dijalankan.
- T3-007 retry backoff dan unit tests offline tersedia; default schedule `10, 30, 90, 270` detik, cap, dan max attempts tervalidasi tanpa `sleep` atau executor.
- T3-008 resume planner dan unit tests offline tersedia; completed inventory jobs tidak diulang, retry/pending/manual review dipisahkan, dan file tanpa checksum tidak otomatis di-skip.
- T3-009 SHA-256 generator dan unit tests offline tersedia; manifest kolom normatif, stable 64-hex hash, path guard, dan atomic CSV write tervalidasi tanpa download atau inventory mutation.
- T3-010 quarantine manager dan unit tests offline tersedia; atomic move fixture, reason JSON, collision/no-overwrite, path guard, dan inventory non-mutation tervalidasi.
- T3-011 daily_full guard dan unit tests offline tersedia; builder/CLI fail-closed sebelum konfigurasi dibaca dan tanpa membuat output; ADR-006 tetap `PROPOSED`.
- T3-012 dataset version/part pin dan unit tests offline tersedia; `202311/default` diambil dari snapshot lokal, manifest batch JSON ditulis atomik, mismatch di tengah batch ditolak fail-closed, dan Graphify code-only refresh terakhir mencatat 555 node, 915 edge, 53 komunitas, serta diagnostics bersih.
- T3-013 log sanitizer dan unit tests offline tersedia; sensitive fields, auth/cookie headers, bearer/basic token, signed-query values, email, user-profile path, dan exception message dirahasiakan tanpa credential read; Graphify code-only refresh terakhir mencatat 580 node, 960 edge, 53 komunitas, serta diagnostics bersih; downloader belum dijalankan.
- AOI aktif regional `eastern_indonesia_regional_001` diterapkan dari bbox user; `pilot_001` tetap terpisah untuk T2. Graphify code-only refresh terakhir mencatat 588 node, 967 edge, 54 komunitas, serta diagnostics bersih; tidak ada operasi Cloud atau download.
- T3-014 executor preparation dan unit tests offline tersedia melalui `python/03_download_glorys.py`; `--execute` menjadi opt-in eksplisit, monthly scalar time boundary, subset AOI/depth/version/part, basic check, retry, checksum, quarantine, manual retry, dan logging tersedia; Graphify code-only refresh terakhir mencatat 655 node, 1.190 edge, 56 komunitas, serta diagnostics bersih. Tidak ada credential read oleh Codex atau rerun network.
- T3-016 rekonsiliasi read-only tersedia melalui `python/05_reconcile_inventory.py`; Graphify code-only refresh terakhir mencatat 714 node, 1.321 edge, 62 komunitas, serta diagnostics bersih. Rekonsiliasi aktual mencatat 165 job/file aktif, 1.125 timestep, 165 checksum cocok, 0 partial, dan 3 quarantine artifact sebagai note.
- T3-017 stage gate tersedia melalui `python/06_generate_stage3_report.py`; laporan final `PASS_WITH_NOTES` dan full offline validation lulus dengan 79 unit test, security scan exit 0, foundation checks exit 0, serta Graphify diagnostics bersih.
- T4 WP-1 validator lokal `python/07_validate_stage4.py` dan fixture unittest tersedia; validation run membaca 165/165 file dengan 165 PASS dan 0 FAIL untuk T4-001..T4-004, tanpa mutasi raw NetCDF atau inventory. Graphify code-only refresh sesudah perubahan mencatat 768 node, 1.427 edge, 71 komunitas, dan diagnostics bersih; T4-005 onward tetap pending.
- T4 WP-2 scope `--scope wp2` memperluas validator ke T4-005..T4-008; 15 fixture tests lulus, 165/165 file PASS, 0 error, dan 5 encoded-range anomaly non-blocking tercatat tanpa silent correction. Final Graphify refresh mencatat 779 node, 1.450 edge, 74 komunitas, diagnostics bersih. T4-009 onward tetap pending.
- T4 full scope `--scope full` menyelesaikan T4-009..T4-014; 22 fixture tests lulus, 165/165 file PASS, 0 error, coverage dan `uo`/`vo` consistency tercatat, distribusi per file/periode tersedia, dan 5 anomaly tetap non-blocking. Graphify final refresh mencatat 801 node, 1.494 edge, 72 komunitas, diagnostics bersih. T5 conversion/cloud tetap downstream.
- M0 tetap `IN_PROGRESS`; status ini tidak mengubah keputusan ADR yang tetap `PROPOSED`.
