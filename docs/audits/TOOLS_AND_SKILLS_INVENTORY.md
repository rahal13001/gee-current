# Tools and Skills Inventory — Foundation/M0

Tanggal audit: 2026-08-02 (Asia/Jayapura)

## Scope dan batas

Pemeriksaan ini read-only dan lokal. Tidak ada login, credential file read, Earth Engine initialization,
Copernicus access, network, install/upgrade, download, upload, IAM, billing, atau operasi Git destruktif.

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
| Python imports | pemeriksaan `ee`, `geemap`, dan dependency inti | MISSING; tidak diinstal |
| EE initialization/auth | sengaja tidak dijalankan | NOT RUN per scope dan security policy |
| Workflow readiness | pola RUN/DATA_LAYER dipetakan | PARTIAL; struktur siap, runtime belum siap |

## Dependency Earth Engine yang kelak diperlukan

`earthengine-api` (`ee`), `geemap`, dan untuk workflow lokal vector `geopandas` (opsional), bersama
dependency Python yang akan dikunci setelah environment dan approval tersedia. Tidak ada paket yang dipasang sesi ini.

## Kesimpulan skill gate

- FND-SKILL-001: `TESTED` pada availability/help/offline invocation; semantic graph evidence tersedia.
- FND-SKILL-002: `TESTED` pada skill/reference/template completeness; `BLOCKED` untuk runtime/auth karena dependency dan Project ID belum tersedia.
