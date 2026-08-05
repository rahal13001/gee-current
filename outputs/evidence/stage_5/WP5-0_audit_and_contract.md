# WP5-0 — Audit dan desain kontrak Tahap 5

Tanggal audit: 2026-08-05 (Asia/Jayapura)  
Waktu evidence: 2026-08-05T06:24:12.0917297Z  
Tahap aktif: Tahap 5 — Konversi dan produk Python  
Work package: WP5-0 — Audit dan desain kontrak  
Status: `PASS_WITH_NOTES` untuk audit offline; implementasi T5 belum dimulai  
Repository: `E:\project\gee-current`  
Branch: `main`  

## Tujuan dan batas audit

Audit ini memeriksa dokumen normatif, status downstream Tahap 4, struktur
repository, dependency lokal yang sudah tersedia, schema konfigurasi, open
decisions, serta kesiapan kontrak T5-001 sampai T5-027. Audit ini tidak membuat
output produksi dan tidak mengubah raw NetCDF, inventory, checksum, quarantine,
metadata snapshot, manifest T4, atau artefak T4.

Batas operasional yang dipatuhi:

- tidak ada login atau authentication;
- tidak ada network, download, upload, atau Earth Engine;
- tidak ada instalasi atau upgrade dependency;
- `daily_full` tetap disabled;
- tidak ada perubahan keputusan ilmiah;
- tidak ada commit, push, reset, clean, checkout, atau penghapusan.

## Requirement dan dependency

Kontrak WP5 mengacu pada `FR-CONV-01` sampai `FR-CONV-07`, `FR-PY-01`
sampai `FR-PY-17`, task `T5-001` sampai `T5-027`, serta test plan
`TST-CONV-001` sampai `TST-CONV-014` dan `TST-PY-001` sampai `TST-PY-030`.
Dependency tahapnya adalah T4-014; backlog dan gate T4 tetap menjadi sumber
kebenaran untuk kesiapan downstream.

### Status T4 yang diverifikasi

- `T4-014`: `PASS_WITH_NOTES`.
- `exit_status=0` pada gate.
- `files_checked=165`, `files_pass=165`, `files_fail=0`, `error_count=0`.
- `anomaly_count=5`; anomaly encoded-range berada dalam kebijakan
  non-blocking dan tidak dikoreksi.
- Manifest T4 berisi 165 entry dengan status `PASS` dan
  `downstream_ready=true`.
- Inventory berisi 132 job `monthly_all`/132 timestep dan 33 job `daily_jfm`/
  993 timestep; seluruh 165 job memiliki checksum; dataset pin konsisten
  `202311/default`.
- `M0` tetap `IN_PROGRESS`; seluruh ADR tetap `PROPOSED`.

T4 menyediakan dependency minimum untuk memulai pilot konversi lokal, tetapi
tidak otomatis menyetujui WP5-1 atau conversion skala collection.

## Kontrak input/output T5

### Input normatif

1. `outputs/manifests/stage_4_validated_manifest.json` sebagai daftar input
   tervalidasi; hanya entry `PASS` yang boleh diproses.
2. Raw NetCDF pada path yang dirujuk manifest, tanpa modifikasi.
3. Konfigurasi aktif untuk periode, depth, AOI, penamaan, dan statistik.
4. Dataset pin `202311/default`, variabel `uo` dan `vo`, unit `m s-1`, depth
   `0.494025 m`, serta periode `2015-01-01` sampai `2026-01-01` eksklusif.

### Kontrak source conversion T5-001—T5-008

Setiap output source harus memenuhi seluruh syarat berikut:

- dtype `float32`;
- tepat dua band, urutan `uo`, lalu `vo`;
- mask/NoData sama secara exact dengan sumber dan zero valid tetap valid;
- CRS dan affine transform konsisten dengan grid sumber;
- tidak ada resampling, warp, atau perubahan orientasi diam-diam;
- timestamp, depth, Product/Dataset ID, dataset version/part, provenance,
  source filename, source checksum, dan pipeline version tersedia;
- comparator melaporkan max absolute error, mean absolute error, percentile
  error, lokasi error maksimum, dan mask equality;
- toleransi numerik awal mengikuti baseline `1e-6 m/s`, tetapi finalisasi
  toleransi float32 tetap mengikuti `OD-007` dan hasil pilot.

T5-008 hanya boleh memproses collection inti setelah T5-001—T5-007 lulus,
manifest tervalidasi direview, dan persetujuan eksplisit tersedia bila
storage/runtime bermakna. Bulk GeoTIFF/raw tidak menjadi artefak commit default.

### Kontrak analytics Python T5-009—T5-025

- `speed = sqrt(uo^2 + vo^2)`;
- mean speed dan kecepatan resultan adalah keluaran terpisah;
- mean `u`/`v` valid-count aware;
- arah adalah arah menuju, clockwise dari utara;
- zero speed dan pembagian nol menghasilkan NoData/`None` sesuai schema,
  bukan infinity atau arah palsu;
- persistence, statistik deskriptif, quantile, climatology, anomaly, trend,
  zonal table, dan raster turunan wajib memuat unit, valid-count, period
  label, parameter metode, mask, dan provenance;
- statistik panjang dan current rose tetap Python/batch, bukan komputasi GEE
  interaktif;
- setiap produk turunan wajib dapat ditelusuri ke entry manifest dan checksum
  sumbernya.

## Keputusan yang masih terbuka atau memblokir produksi

| Area | Status | Konsekuensi |
|---|---|---|
| T5-016 variance/SD | `BLOCKED/TBD` | `ddof` harus disetujui sebelum output GLORYS produksi. |
| T5-016 P10—P99 | `BLOCKED/TBD` | `percentile_method` sudah memiliki implementasi `linear`, tetapi belum menjadi keputusan produksi. |
| T5-017 threshold | `BLOCKED` | Sumber threshold, unit, bin, batas inklusif/eksklusif, NoData, reference period, dan target speed/komponen belum ditetapkan. |
| T5-019 current rose | `BLOCKED` | Speed bins dan aturan yang bergantung pada threshold belum disetujui. |
| T5-020—T5-022 | `BLOCKED/TBD` | Weighting climatology dan reference period eksplisit belum ditutup secara tertulis. |
| T5-023 trend | `BLOCKED/TBD` | Metode, uncertainty, dan batas interpretasi eksploratif belum ditetapkan untuk output produksi. |
| T5-024—T5-025 | `BLOCKED_WITH_NOTES` | AOI tersedia sebagai bbox user-provided; polygon perairan/water mask belum memiliki provenance yang cukup untuk klaim zonal. |
| T5-008 | `PENDING_APPROVAL` | Conversion collection 1.125 timestep menunggu pilot lulus dan persetujuan skala/storage/runtime. |

Tidak ada nilai threshold, bin, weighting, ddof, reference period, atau metode
trend yang diciptakan dalam audit ini.

## Acceptance criteria setiap work package

| Work package | Acceptance criteria |
|---|---|
| WP5-0 | Audit dokumen/status/dependency/schema selesai; open decisions terdaftar; tidak ada output produksi; evidence command/exit/evidence/limitation lengkap; persetujuan diminta sebelum WP5-1. |
| WP5-1 | T5-001—T5-007 lulus pada fixture sintetis dan pilot lokal kecil: float32, band order, mask exact, CRS/transform, no resampling, metadata/checksum, dan comparator numerik. |
| WP5-2 | T5-008 hanya memakai manifest T4 tervalidasi; seluruh output terinventaris, checksum dan provenance lengkap; storage/runtime serta bulk-output policy disetujui. |
| WP5-3 | T5-009—T5-016 dan T5-018 lulus unit/synthetic/regression: kardinal, zero speed, mask, valid-count, cancellation mean/resultant, wrap-around north, persistence, statistik, dan quantile method terdokumentasi. |
| WP5-4 | T5-020—T5-023 memiliki weighting/reference/method tertulis, label periode, unit, mask, provenance, serta caveat trend eksploratif; tidak ada parameter yang ditebak. |
| WP5-5 | T5-024—T5-025 hanya memakai AOI/geometri berprovenance; tabel/raster memiliki area, valid-count, metadata, checksum, dan deterministic rebuild evidence. |
| WP5-6 | T5-017 dan T5-019 hanya dikerjakan setelah threshold, bins, NoData, reference period, dan target variable disetujui; arah menuju dan caveat resultan rendah wajib jelas. |
| WP5-7 | T5-026—T5-027 memiliki product manifest/checksum, traceability, evidence index, regression/security/full checks, limitations, dan gate yang tidak menyatakan PASS tanpa bukti lengkap. |

## Pemeriksaan offline dan evidence

| Command/check | Exit | Hasil |
|---|---:|---|
| `check_secrets.ps1 -Root E:\\project\\gee-current` | 0 | Tidak ada potential secret; dua documentation placeholder diklasifikasikan dan nilainya tidak dicetak. |
| `run_foundation_checks.ps1 -Root E:\\project\\gee-current -ReadOnly` | 0 | Foundation checks menghasilkan `TST-SEC-BASELINE=PASS`, root instruction check PASS, dan anchor check `PASS_WITH_NOTES`. |
| `git diff --check` | 0 | Tidak ada whitespace error pada worktree saat audit. |
| Full local unittest via `.venv\\Scripts\\python.exe` dengan `PYTHONPATH` root | 0 | 101 test, 0 failure, 0 error; `pytest` tidak tersedia dan tidak diinstal. |
| `.venv\\Scripts\\python.exe -m pip check` | 0 | No broken requirements found. |
| Graphify query existing graph | 0 | Query offline terhadap `graphify-out/graph.json`; tidak ada network. |

Dependency yang terdeteksi: Python 3.12.13, NumPy 2.5.1, xarray 2026.7.0,
h5netcdf 1.8.1, rasterio 1.5.0, rioxarray 0.23.0, pandas 3.0.5,
dask 2026.7.1, dan zarr 3.3.0.

Config/manifest hash yang digunakan sebagai konteks audit:

```text
E52A4B903FA55323BD4A979A950F8712FF75CDF0169B38A3BF0508E59287AF2C  config/analysis_period.json
7CAB31FA01FC9C9D47BF0AF00E786358D82D0AADB38A6F771905B1D5A51A63B5  config/depth_selection.json
B2E225934EAFD892263F97B1415B89A30C642EBFAF6E8436D279E6EA7C6461A8  config/statistics.json
7D8EEA70B7618965088E7395FC02FC8961E8D60C37CFD00C36D385D77565710C  config/study_area.json
E47A828D5E2F1A74E578C7198FA9C09D03CF0D5350826BD5116A02CB1364CA44  config/architecture_manifest.json
20675C5F1523FFF08367A2C3EF0E9ED493F215A8B39690FD2F192AC178610D74  config/asset_naming.json
7AA991F6E529E11F12A72BDC1374437EF7E7F487C286BABC8581C5D9E47CFFB5  config/interactive_limits.json
5E0D335B0060DFA7E5BAD2DE7649099FCE350B7C37B8699DE6D1E781DC203089  outputs/manifests/stage_4_validated_manifest.json
```

## Limitation dan status berikutnya

Audit ini tidak membuktikan T5-001—T5-027, tidak menghasilkan GeoTIFF
produksi, tidak menutup open decisions, dan tidak mengubah status backlog T5.
Graphify refresh penuh belum dijalankan karena perubahan kode belum terjadi;
setelah perubahan kode/dokumentasi WP berikutnya, refresh offline wajib
dijalankan sesuai instruksi proyek.

Rekomendasi: `WP5-0 = PASS_WITH_NOTES`, lalu berhenti pada approval gate.
WP5-1 dapat dimulai hanya setelah persetujuan eksplisit pengguna. T5-017 dan
T5-019 tetap `BLOCKED`; M0 tetap `IN_PROGRESS`; ADR tetap `PROPOSED`.
