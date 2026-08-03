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
- Menambahkan modul formula metodologi T1 untuk speed, mean/resultant, bearing,
  persistence, dan perlindungan zero-vector dengan uji sintetis kardinal.
- Menambahkan baseline statistik deskriptif T1 dengan `ddof` dan metode persentil
  eksplisit; threshold tetap `TBD` dan belum dipakai pada data operasional.
- Memperketat validasi konfigurasi lintas-file untuk dataset IDs, periode JFM,
  depth selection, daftar statistik, timezone, dan status parameter terbuka.
- Merekam hasil user-managed active describe product/daily dan 50 depth levels
  nyata; validator depth kini menerima urutan monotonic ascending maupun
  descending positive-down tanpa mengubah target `0.494025 m`.
- Mencatat unduhan user-managed NetCDF pilot dan validasi lokal T2-004–T2-011:
  retry menghasilkan tepat 29 timestep Februari 2020; variabel, unit, depth,
  grid, mask, CF packing, dan range tervalidasi dengan `PASS_WITH_NOTES`.
  GeoTIFF, upload, dan operasi Earth Engine belum dijalankan; M0 tetap `IN_PROGRESS`.
- Mencatat T2-012 sebagai `BLOCKED` setelah preflight lokal menemukan
  `rasterio`, `rioxarray`, dan GDAL tidak tersedia pada approved `.venv`;
  dependency installation tidak dilakukan.
- Setelah persetujuan user, menambahkan `rasterio==1.5.0` dan
  `rioxarray==0.23.0`, memperbarui lock menjadi 91 package versions, membuat
  konverter GeoTIFF reusable, menghasilkan 29 GeoTIFF, dan memvalidasi
  NetCDF–GeoTIFF dengan maksimum selisih absolut `2.98e-08`.
- Menutup T0-012 sebagai `PASS_WITH_NOTES` setelah product, daily, monthly,
  depth, dan material-change evidence user-managed lengkap tercatat.
- Menetapkan AOI `pilot_001` dan menambahkan T2 offline preflight/dry-run yang
  memvalidasi 29 tanggal Februari 2020 tanpa download atau upload.
- Menambahkan helper `tools/gee_export_corrected_pilot_assets.js` untuk ekspor
  tiga aset pilot corrected dengan pemetaan band `b1/b2` menjadi `uo/vo`,
  timestamp eksplisit, dan asset ID literal yang aman untuk task Code Editor.
