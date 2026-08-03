# Changelog

## Unreleased

- Membentuk baseline Foundation/M0: instruksi root, `.gitignore`, struktur evidence,
  governance record, audit tooling, ADR baseline berstatus `PROPOSED`, dan status/traceability.
- Menambahkan audit Graphify dan inventaris pemeriksaan GEEMu secara offline.
- Merekonsiliasi evidence setup dan governance berdasarkan laporan user: Project ID
  `ee-rahal13001`, registrasi nonkomersial, Earth Engine smoke test, serta versi dependency
  lokal yang dilaporkan; tidak ada login atau autentikasi ulang oleh Codex.
- Menandai FND-007, FND-009, FND-010, dan FND-019 sebagai `PASS_WITH_NOTES`; M0
  menyelesaikan final offline gate sebagai `PASS` dengan catatan.
- FND-019 hanya mencakup evidence lokal. GitHub push protection, secret scanning, ruleset,
  dan branch protection remote belum diaudit. Evidence FND-010 berasal dari review user-managed;
  exact tier, AOI, dan asset root tidak diklaim.
- Merekam `requirements.txt` dan `requirements-lock.txt` dari `.venv` yang disetujui user;
  FND-006 menjadi `PASS_WITH_NOTES` setelah `pip check` exit 0. Clean-room reinstall belum dilakukan.
- Menambahkan mode `-ReadOnly` pada foundation runner dan merekonsiliasi evidence FND-010;
  quota/EECU usage `0`, project tidak terhubung billing account, IAM `Owner`, dan resource inventory
  user-managed dicatat tanpa operasi Cloud.
- Menambahkan baseline konfigurasi Tahap 0–1: AOI pilot, periode analisis, depth,
  statistik, asset naming, schema pilot, metadata snapshot, dan validator offline.

- Menambahkan wrapper `describe` plan-only, validator depth fail-closed, metadata
  compatibility guard, dan evidence Tahap 0; eksekusi metadata aktif tetap ditunda
  sampai network/authentication diizinkan.
