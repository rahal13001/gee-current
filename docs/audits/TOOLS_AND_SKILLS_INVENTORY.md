# Tools and Skills Inventory — Foundation/M0

Tanggal audit: 2026-08-03 (Asia/Jayapura)

## Scope dan batas

Pemeriksaan ini read-only dan offline untuk aktivitas Codex. Tidak ada login ulang, credential file read,
Earth Engine initialization ulang, Copernicus access ulang, network, install/upgrade, download, upload,
IAM, billing, atau operasi Git destruktif. Runtime/setup facts yang ditandai user-reported berasal dari
laporan pengguna dan bukan hasil eksekusi ulang.

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
| Workflow readiness | pola RUN/DATA_LAYER dipetakan | PARTIAL; AOI, asset root, exact tier, IAM, billing, EECU belum diaudit |

## Dependency Earth Engine yang kelak diperlukan

`earthengine-api` (`ee`) dan dependency Python lain yang akan dikunci setelah environment dan approval tersedia.
`geemap`/`geopandas` tidak diklaim terpasang dari evidence user yang tersedia. Tidak ada paket yang dipasang sesi ini.

## Kesimpulan skill gate

- FND-SKILL-001: `TESTED` pada availability/help/offline invocation; semantic graph evidence tersedia.
- FND-SKILL-002: `TESTED_WITH_NOTES` pada skill/reference/template completeness dan user-reported runtime smoke;
  tidak ada klaim audit exact tier, IAM, billing, EECU, asset root, atau AOI.
