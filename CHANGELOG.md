# Changelog

## Unreleased

- Menyelesaikan koreksi runtime T6-006 pada sampel GEE: dua aset `_fixed`
  tervalidasi, lalu dua ID kanonis lama yang salah dihapus dan dibuat ulang
  dengan band source `uo`/`vo` serta derived `speed`. Dua task rekreasi
  berstatus `completed`; `_fixed` dipertahankan sebagai rollback/evidence dan
  `daily_full` tetap tidak diaktifkan.

- Menyelesaikan T6-004 secara offline: generator membuat satu manifest source
  daily JFM dan satu manifest derived `speed`, dengan checksum, grid, waktu
  end-exclusive, provenance, dan limitation lengkap. URI GCS masih sample;
  tidak ada autentikasi, upload, atau task GEE.

- Menyelesaikan T6-002/T6-003 secara offline dengan schema manifest source dan
  derived. Kontrak mengunci struktur manifest, band/missing data, metadata PRD,
  provenance, grid/mask, period end-exclusive, lima product type derived lokal,
  dan limitations; tidak ada operasi GEE atau cloud.

- Menyelesaikan T6-001 sebagai review governance GEE read-only dengan
  `PASS_WITH_NOTES`: Project ID dan prefix asset root konsisten secara lokal,
  evidence user-managed dipisahkan dari temuan yang belum terverifikasi, dan
  tidak ada login, credential read, network, upload, export, atau task cloud.
  T6-002/T6-003 direkomendasikan sebagai pekerjaan schema berikutnya.

- Menutup rekonsiliasi T5-028 dengan `PASS_WITH_NOTES`: environment Windows
  mencatat Python 3.12.13, pytest 9.1.1, `pip check` lulus, dan 116 test serta
  29 subtest lulus. Dependency test runner direkam dalam lock; Graphify
  diselaraskan dengan evidence terbaru. T6 tetap memerlukan approval transisi.

- Menambahkan WP5-5/T5-028 sebagai gate administratif untuk rekonsiliasi status,
  evidence, environment test, dan Graphify sebelum transisi ke Tahap 6. Tidak
  ada keputusan ilmiah, data, formula, atau operasi cloud yang diubah.

- Menyelesaikan WP5-4/T5-020..T5-023 melalui audit penerimaan offline yang
  merekonsiliasi 132 frame monthly dan 993 frame JFM, memverifikasi 12
  klimatologi bulanan, 1 klimatologi JFM, 1.125 anomali, dan 1 tren OLS
  eksploratif, serta mencatat weighting, baseline, reference period, checksum,
  schema, dan provenance pada manifest WP5-4.

- Memperbarui WP5-3 analytics lokal berdasarkan keputusan ahli: threshold global
  AOI P90 per analysis plan, valid-area QC 0,95, current rose 16 sektor
  `towards` dengan global quantile bins, tabel threshold/rose, dan 2 SVG AOI.
  Produk zona menunggu geometri valid; metodologi tidak diperlakukan sebagai
  ambang keselamatan atau operasional.

- Memperkuat audit WP5-3: current-rose ZERO tidak diberi sektor, static
  expected-ocean mask disimpan dan diaudit, config hash mencakup seluruh config
  analytics, metadata dataset wajib berasal dari manifest T4, dan figure SVG
  menampilkan periode/unit/bin dalam `m s-1`.

- Menyelesaikan WP5-2/T5-008 conversion collection lokal: 165/165 entry
  tervalidasi dan 1.125/1.125 timestep menghasilkan GeoTIFF terinventaris
  dengan checksum/provenance; audit metadata dan comparator numerik seluruh
  collection lulus pada toleransi 1e-6. Output raster tetap lokal/diabaikan
  Git; WP5-3 analytics kemudian dijalankan setelah keputusan metodologi disahkan.

- Menyelesaikan WP5-1 conversion pilot lokal melalui `python/conversion.py` dan
  comparator manifest-scoped. Fixture synthetic 5/5 lulus; satu job T4
  tervalidasi menghasilkan 29 GeoTIFF float32 dua-band dengan mask, transform,
  metadata, checksum, dan perbandingan numerik lulus. T5-008 collection
  conversion tetap menunggu persetujuan.

- Menambahkan audit offline WP5-0 dan kontrak Tahap 5 di
  `outputs/evidence/stage_5/WP5-0_audit_and_contract.md`. Audit memverifikasi
  dependency T4-014, schema input/output, dependency lokal, open decisions,
  serta acceptance criteria; belum ada output produksi dan WP5-1 menunggu
  persetujuan eksplisit.

- Menyelesaikan Tahap 4 T4-009–T4-014 melalui scope `--scope full`: coverage
  valid, konsistensi `uo`/`vo` mask/time/grid, distribusi per file/periode,
  validated manifest, laporan PASS/FAIL, dan gate Tahap 4. Validasi 165/165
  file menghasilkan 0 error dan keputusan `PASS_WITH_NOTES`; lima anomaly
  encoded-range tetap dicatat tanpa koreksi data. T5 conversion dan operasi
  cloud tetap downstream.
- Menyelesaikan Tahap 4 WP-2 melalui scope `--scope wp2`: validasi mask/fill,
  orientasi koordinat, raw/decoded scale-offset, dan plausibility pada 165 file.
  Hasilnya 165 PASS, 0 error, dan 5 anomaly encoded-range non-blocking; tidak ada
  nilai data yang dikoreksi. T4-009 onward tetap pending.
- Menambahkan validator lokal read-only Tahap 4 WP-1 melalui
  `python/07_validate_stage4.py` untuk T4-001..T4-004. Fixture unittest nominal,
  missing `vo`, bad unit, bad depth, missing/duplicate timestamp, monthly, dan
  leap-year lulus; validasi 165 file aktif menghasilkan 165 PASS dan 0 FAIL.
  Manifest hanya memuat file PASS. T4-005 onward tetap pending dan gate T4-014
  diberi scope WP-1 dengan status `PASS_WITH_NOTES`.
- Menambahkan persiapan executor T3-014 melalui `python/03_download_glorys.py`.
  Executor membangun plan lokal, membentuk subset Copernicus dengan AOI/depth/
  version/part eksplisit, menyiapkan inventory SQLite/CSV, melakukan basic
  check/checksum/quarantine/logging, dan mendukung retry/resume. Mode aktual
  hanya aktif dengan `--execute`; autentikasi, network, dan download belum
  dilakukan. T3-014 tetap `NOT_STARTED`.
- Memperbaiki batas waktu monthly T3-014 setelah respons Copernicus menghasilkan
  timestamp bulan berikutnya: subset monthly kini meminta timestamp scalar dengan
  `start_datetime == end_datetime`. Menambahkan recovery eksplisit untuk job
  `failed_permanent` setelah quarantine melalui `--job-id --force-after-quarantine`;
  transisi ilegal normal tetap ditolak.
- Memperbaiki resume lintas batch T3-014/T3-015: inventory SQLite kini memvalidasi
  job secara plan-scoped dan executor hanya memproses plan aktif, sehingga 132 job
  `monthly_all` yang sudah selesai dapat tetap berada dalam database saat
  `daily_jfm` ditambahkan. Regresi offline lulus dengan 8/8 test.
- Memperbaiki batas waktu request daily JFM: executor kini mengirim timestamp
  terakhir pada `00:00:00` berdasarkan jumlah timestep yang diharapkan, sehingga
  endpoint `23:59:59` tidak lagi menarik hari pertama bulan berikutnya.
- Menambahkan T3-016 `python/05_reconcile_inventory.py` untuk rekonsiliasi
  read-only plan, SQLite inventory, file aktif, SHA-256, partial, dan quarantine.
  Rekonsiliasi aktual menemukan 165/165 file aktif dan checksum cocok; tiga file
  quarantine lama dipertahankan sebagai audit evidence.
- Menambahkan T3-017 `python/06_generate_stage3_report.py` untuk laporan dan
  gate Tahap 3. Cross-check final menghasilkan 165 job, 1.125 timestep, 165
  checksum cocok, dan keputusan `PASS_WITH_NOTES`; status T3-014 sampai T3-017
  diperbarui setelah instruksi eksplisit user.
- Menyelaraskan dokumentasi pra-T4: `PASS_WITH_NOTES` diterima hanya untuk note
  non-blocking, kontrak validated manifest/report ditetapkan, batas T4 local/offline
  dicatat, dan status Tahap 4 tetap `NOT_STARTED` sampai persetujuan user.
- Mencatat proposal AOI ekspansi terpisah untuk perairan Papua, Maluku, dan
  Maluku Utara di `docs/AOI_EXPANSION_PROPOSAL.md` dan menerapkan bbox user ke
  `config/study_area.json` sebagai AOI aktif `eastern_indonesia_regional_001`.
  `pilot_001` tetap terpisah; polygon perairan, water mask, dan download
  regional belum ditetapkan atau dijalankan.
- Menyelesaikan T3-013 sanitizer log offline melalui `python/log_sanitizer.py`.
  Sanitizer meredaksi field sensitif, auth/cookie header, bearer/basic token,
  signed-query values, email, user-profile path, dan exception message tanpa
  membaca credential; executor unduhan belum tersedia atau dijalankan.
- Menyelesaikan T3-012 pin dataset version/part secara offline: `python/dataset_pin.py`
  mengambil `202311/default` dari snapshot lokal, memvalidasi semua job terhadap pin,
  dan menulis manifest batch JSON secara atomik. Perubahan version/part di tengah batch
  ditolak fail-closed; tidak ada executor atau download.
- Menyelesaikan T3-011 guard `daily_full`: `DailyFullDisabledError` menolak
  permintaan pada builder sebelum konfigurasi dibaca, CLI mengembalikan exit
  `2`, dan tidak ada plan/output yang dibuat. ADR-006 tetap `PROPOSED`.
- Menambahkan T3-010 `python/quarantine.py` untuk memindahkan file invalid
  secara atomik ke direktori timestamped dengan `reason.json`. Collision,
  overwrite, path escape, dan inventory non-mutation diuji offline; manager
  hanya bekerja pada path lokal eksplisit.
- Menambahkan T3-009 `python/checksum.py` untuk SHA-256 file lokal secara
  chunked dan manifest `job_id, relative_path, size_bytes, sha256,
  calculated_utc` dengan atomic replace. Hash stabil dan guard path/file diuji
  offline; inventory tidak dimutasi dan download belum dijalankan.
- Menambahkan T3-008 `python/resume.py` untuk resume planning offline dari
  inventory: job selesai tidak diulang, pending/retry dipisahkan, dan
  `failed_permanent`/`quarantined` ditahan untuk manual review. File tanpa
  checksum tidak otomatis dianggap valid; executor dan download belum dibuat.
- Menambahkan T3-007 `python/retry_backoff.py` dengan policy exponential
  backoff job-level `10, 30, 90, 270` detik, cap maksimum, dan batas empat
  attempt. Perhitungan deterministik diuji offline tanpa `sleep`, executor,
  network, atau download.
- Menambahkan T3-006 `python/retry_classifier.py` untuk mengklasifikasikan
  error retryable/permanent sesuai aturan Tahap 3, termasuk HTTP 408/429/5xx,
  dan fail-closed ke permanent untuk kondisi tak dikenal. Unit test offline
  lulus melalui `unittest`; executor, backoff, dan download belum dikerjakan.
- Menambahkan T3-005 ekspor inventory CSV melalui `InventoryStore.export_csv`.
  Output memiliki header/field yang sama dengan SQLite, urutan deterministik, dan
  atomic replace; konsistensi diuji offline. Retry, checksum, quarantine, dan
  batch belum dikerjakan.
- Menambahkan T3-004 `python/inventory.py` untuk inventory SQLite offline dengan
  16 kolom job, state machine Tahap 3, constraint status, dan trigger penolak
  transisi ilegal. Unit test offline lulus melalui `unittest`; `pytest` tidak
  tersedia pada `.venv` dan tidak diinstal. T3-005 CSV, retry, checksum,
  quarantine, dan batch tetap belum dikerjakan.
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
- Menambahkan jalur normalisasi 26 asset pilot yang belum diperbaiki dan validator read-only
  Earth Engine untuk seluruh 29 asset corrected; schema `uo,vo`, timestamp, pemetaan band,
  statistik AOI, dan uji arah kardinal tercatat dengan `PASS_WITH_NOTES`.
- Menambahkan validasi reference-point Pythonâ€“GEE pada 116 pasangan titik-waktu dengan zero mask
  mismatch dan error maksimum sub-`1e-7`, serta benchmark B1 29/29 citra dengan `PASS_WITH_NOTES`;
  B2/B3 tetap menunggu aset JFM/full-series.

- Menambahkan wrapper `describe` plan-only, validator depth fail-closed, metadata
  compatibility guard, dan evidence Tahap 0; eksekusi metadata aktif tetap ditunda
  sampai network/authentication diizinkan.
- Menambahkan builder plan Tahap 3 offline untuk 132 job bulanan dan 33 job JFM/993 timestep;
  `daily_full` tetap ditolak fail-closed dan belum ada download atau akses network.
- Menambahkan helper display read-only untuk asset corrected dan melengkapi script ekspor masa depan
  dengan provenance product/dataset/version/part, depth, dan unit; asset yang sudah ada tidak ditimpa.
- Menetapkan keputusan untuk mempertahankan 29 asset pilot yang sudah tervalidasi; speed tetap
  menjadi derived image band dari `uo` dan `vo`, bukan band permanen yang diduplikasi.
- Menyegarkan inventaris skill, traceability asset root, dan audit Graphify code-only sebelum handoff
  T3; Graphify mencatat 321 node/410 edge pasca-cluster dengan diagnostics tanpa endpoint bermasalah.
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
- Menambahkan helper read-only `tools/gee_validate_corrected_pilot_assets.js`
  serta evidence T2-014–T2-016 untuk filter eksklusif, statistik AOI ringan,
  dan uji arah kardinal GEE pada tiga aset sampel.
