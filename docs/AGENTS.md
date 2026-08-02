# AGENTS.md — GLORYS12V1 Current Research & Teaching System

**Status:** Instruksi normatif repository  
**Berlaku untuk:** Seluruh repository, kecuali digantikan secara eksplisit oleh `AGENTS.override.md` atau `AGENTS.md` yang lebih dekat dengan direktori kerja  
**Ruang penggunaan:** Pendidikan dan penelitian nonkomersial  
**Fokus ilmiah:** Arus laut GLORYS12V1  
**Bahasa dokumentasi utama:** Bahasa Indonesia  
**Terakhir diperbarui:** 31 Juli 2026

---

## 1. Tujuan dokumen

Dokumen ini menetapkan cara Codex bekerja di repository pengembangan sistem analisis arus laut Copernicus Marine GLORYS12V1 dengan Python dan Google Earth Engine.

Codex wajib:

- mengikuti sumber kebenaran proyek;
- mengerjakan tahap aktif saja;
- menjaga integritas ilmiah;
- tidak melewati gerbang validasi;
- tidak menyimpan atau membaca rahasia pengguna;
- tidak mengklaim keberhasilan tanpa bukti;
- mengutamakan arsitektur hibrida Python–GEE;
- menjaga sistem tetap cocok untuk pendidikan dan penelitian nonkomersial.

Kata **WAJIB**, **DILARANG**, **HARUS**, dan **TIDAK BOLEH** bersifat normatif.

---

## 2. Sumber kebenaran dan urutan prioritas

Sebelum mengubah kode, Codex wajib membaca sumber berikut sesuai urutan:

1. `PRD.md` atau `PRD_GLORYS_Current_Research_Teaching_System.md`;
2. `docs/stages/Tahap_0_Verifikasi_Sumber_Data_GLORYS12V1_v1.1.md`;
3. `docs/stages/Tahap_1_Desain_Metodologi_dan_Arsitektur_GLORYS12V1_GEE_v1.1.md`;
4. `docs/stages/Tahap_2_Pilot_End_to_End_GLORYS12V1_GEE_v1.1.md`;
5. `docs/stages/Tahap_3_Otomasi_Unduhan_GLORYS12V1_v1.1.md`;
6. `docs/IMPLEMENTATION_STATUS.md`;
7. `docs/REQUIREMENTS_TRACEABILITY.md`;
8. ADR yang relevan pada `docs/adr/`;
9. dokumentasi modul dan tests terkait.

Jika nama atau lokasi dokumen berbeda, Codex harus mencari dokumen yang ekuivalen sebelum mengubah kode.

### 2.1 Konflik sumber

Urutan penyelesaian konflik:

1. instruksi sistem atau keamanan platform;
2. permintaan eksplisit pengguna pada tugas aktif;
3. `AGENTS.md` yang paling dekat dengan direktori kerja;
4. PRD terbaru yang disetujui;
5. dokumen tahap terbaru;
6. ADR yang telah diterima;
7. kode dan tests yang sudah ada.

Jika PRD, dokumen tahap, ADR, kode, dan test tidak konsisten:

- jangan memilih secara diam-diam;
- catat konflik;
- hentikan perubahan yang bergantung pada konflik;
- minta keputusan pengguna apabila konflik tidak dapat diselesaikan dari sumber proyek.

---

## 3. Batas ruang lingkup

### 3.1 Termasuk

- arus laut;
- Copernicus Marine GLORYS12V1;
- komponen `uo` dan `vo`;
- analisis lapisan model teratas;
- periode 2015–2025;
- analisis Januari–Maret;
- Python, xarray, NetCDF, GeoTIFF/COG;
- Earth Engine Assets, JavaScript API, dan GEE App;
- validasi, statistik, visualisasi, ekspor, dan materi pembelajaran.

### 3.2 Tidak termasuk

Tanpa perubahan PRD dan persetujuan pengguna, Codex dilarang menambahkan:

- analisis gelombang;
- HYCOM, ERA5, atau dataset lain sebagai dataset utama;
- penggabungan GLORYS12V1 dan HYCOM menjadi satu deret waktu;
- data harian seluruh 2015–2025 sebagai default;
- seluruh 50 kedalaman;
- pemodelan pasang surut lokal;
- desain teknik bangunan laut;
- sistem navigasi atau keselamatan operasional;
- penggunaan komersial;
- penggunaan operasional pemerintah;
- backend produksi berbayar;
- layanan Cloud tambahan yang berpotensi menimbulkan biaya.

Dataset lain hanya boleh dipakai sebagai pembanding, validasi, atau demonstrasi yang diberi label jelas.

---

## 4. Keputusan ilmiah yang tidak boleh diubah diam-diam

```text
Product ID:
GLOBAL_MULTIYEAR_PHY_001_030

Dataset harian:
cmems_mod_glo_phy_my_0.083deg_P1D-m

Dataset bulanan:
cmems_mod_glo_phy_my_0.083deg_P1M-m

Variabel:
uo
vo

Satuan:
m s-1

Kedalaman awal:
0.494025 m

Label:
arus dekat permukaan pada lapisan model teratas

Periode:
2015-01-01 sampai 2025-12-31

Batas akhir eksklusif:
2026-01-01

Jumlah tahun:
11

Data inti:
132 timestep bulanan
993 timestep harian Januari–Maret
1.125 timestep total
```

Product ID, Dataset ID, versi dataset, dataset part, variabel, satuan, kedalaman, dan cakupan waktu tetap harus diverifikasi dari metadata aktif sebelum operasi jaringan atau batch.

Jika metadata aktif berubah secara material:

- pipeline harus **fail closed**;
- simpan snapshot metadata;
- jangan meneruskan unduhan;
- dokumentasikan dampaknya;
- perbarui PRD/dokumen tahap hanya setelah disetujui.

---

## 5. Prinsip ilmiah wajib

1. **Scientific-first.**
2. **Reproducible.**
3. **No false precision.**
4. **Source data preserved.**
5. **Heavy compute outside interactive GEE.**
6. **Precompute before publish.**
7. **Explicit metadata.**
8. **Fail closed.**
9. **No silent correction.**
10. **Education-friendly without removing scientific meaning.**

### 5.1 Status data

GLORYS12V1 adalah reanalisis model, bukan pengukuran langsung.

Semua keluaran harus menjelaskan bahwa:

- resolusi sekitar 1/12° tidak mewakili proses lokal beresolusi tinggi;
- konstituen pasang surut tidak dimasukkan;
- selat sempit, teluk kecil, terumbu, dan garis pantai kompleks dapat tidak terwakili;
- data tidak boleh menjadi satu-satunya dasar desain teknik, keselamatan, atau keputusan operasional berisiko tinggi.

### 5.2 Larangan ketelitian semu

Codex dilarang:

- melakukan resampling ke resolusi sangat tinggi lalu mengklaim akurasi meningkat;
- menggunakan skala analisis jauh lebih halus daripada grid sumber tanpa alasan visual yang terdokumentasi;
- menyebut lapisan teratas sebagai 0 m;
- menyebut maksimum data harian sebagai maksimum sesaat;
- menyamakan data model dengan observasi lapangan.

---

## 6. Rumus dan konvensi wajib

### 6.1 Kecepatan per observasi

\[
S_i=\sqrt{u_i^2+v_i^2}
\]

### 6.2 Rata-rata besar kecepatan

\[
\overline{S}=\frac{1}{n}\sum_{i=1}^{n}\sqrt{u_i^2+v_i^2}
\]

### 6.3 Komponen rata-rata

\[
\overline{u}=\frac{1}{n}\sum_{i=1}^{n}u_i
\]

\[
\overline{v}=\frac{1}{n}\sum_{i=1}^{n}v_i
\]

### 6.4 Kecepatan resultan

\[
S_R=\sqrt{\overline{u}^2+\overline{v}^2}
\]

### 6.5 Persistensi

\[
P=\frac{S_R}{\overline{S}}
\]

Pembagian nol harus dimask atau ditangani secara eksplisit.

### 6.6 Arah

Konvensi arah arus:

- menunjukkan **ke mana arus bergerak**;
- 0° = utara;
- 90° = timur;
- 180° = selatan;
- 270° = barat;
- dihitung dari komponen, bukan rata-rata aritmetika sudut.

Empat test kardinal wajib:

| `u` | `v` | Hasil |
|---:|---:|---:|
| 0 | 1 | 0° |
| 1 | 0 | 90° |
| 0 | -1 | 180° |
| -1 | 0 | 270° |

Codex tidak boleh mengklaim arah benar sebelum test Python dan GEE lulus.

---

## 7. Arsitektur sistem wajib

Arsitektur utama adalah hibrida:

```text
Copernicus Marine
        ↓
Python ingestion
        ↓
Raw NetCDF
        ↓
Python validation
        ↓
Validated NetCDF
      ↙         ↘
Python analytics  GeoTIFF conversion
      ↓                 ↓
Precomputed data    GEE source assets
      ↘                 ↙
       GEE derived assets
               ↓
        GEE modules/App
```

### 7.1 Tanggung jawab Python

Python wajib menangani komputasi berat:

- verifikasi metadata;
- unduhan;
- retry dan resume;
- validasi NetCDF;
- decoding;
- checksum dan provenance;
- konversi raster;
- persentil panjang;
- current rose;
- klimatologi;
- anomali;
- tren eksploratif;
- statistik zonal besar;
- produk prahitung;
- keluaran referensi untuk validasi GEE.

### 7.2 Tanggung jawab GEE

GEE digunakan untuk:

- penyimpanan aset terpilih;
- peta;
- filter tanggal;
- interaksi AOI;
- statistik ringan;
- visualisasi vektor;
- grafik sederhana;
- pembacaan produk prahitung;
- ekspor pengguna;
- GEE App.

GEE App tidak boleh menghitung ulang seluruh 2015–2025 pada setiap interaksi.

---

## 8. Tahap dan gerbang pembangunan

| Tahap | Fokus |
|---|---|
| 0 | Verifikasi sumber data |
| 1 | Metodologi dan arsitektur |
| 2 | Pilot end-to-end dan benchmark |
| 3 | Otomasi unduhan |
| 4 | Validasi NetCDF skala inti |
| 5 | Konversi dan produk Python |
| 6 | Publikasi aset GEE terpilih |
| 7 | Modul analisis GEE |
| 8 | Visualisasi vektor |
| 9 | GEE App |
| 10 | Validasi ilmiah dan penerimaan |

### 8.1 Aturan gerbang

Codex wajib:

- mengidentifikasi tahap aktif sebelum bekerja;
- mengerjakan requirement tahap aktif;
- tidak melompat ke tahap berikutnya;
- mencatat bukti PASS;
- menghentikan pipeline pada error kritis.

Codex dilarang memulai:

- unduhan skala penuh sebelum pilot data asli lulus;
- konversi skala penuh sebelum Tahap 4 lulus;
- upload skala penuh sebelum konversi tervalidasi;
- GEE App sebelum pipeline dan benchmark lulus;
- data harian penuh sebelum approval gate khusus.

### 8.2 Status penerimaan

Gunakan status:

```text
NOT_STARTED
IN_PROGRESS
IMPLEMENTED
TESTED
PASS
PASS_WITH_NOTES
BLOCKED
DEFERRED
FAIL
```

Untuk fitur komputasi:

```text
PASS_INTERACTIVE
PASS_BATCH
PASS_PYTHON_ONLY
FAIL_REDESIGN_REQUIRED
```

`PASS_PYTHON_ONLY` dapat diterima untuk komputasi berat yang memang dialihkan ke Python.

---

## 9. Guardrail Google Earth Engine

### 9.1 Batas interaktif awal

| Parameter | Batas |
|---|---|
| Kedalaman | satu |
| AOI | satu per analisis |
| Data harian | maksimum satu tahun atau satu JFM |
| Seluruh 2015–2025 | produk prahitung |
| Skala | native |
| Banyak zona | batch atau tabel prahitung |
| Current rose panjang | Python |
| Persentil panjang | Python atau batch |

Batas hanya boleh diubah setelah benchmark dan dokumentasi.

### 9.2 Pola dilarang pada seri besar

```javascript
collection.toArray()
collection.toBands()
collection.toList(collection.size())
```

Hindari:

- `clip()` pada setiap citra;
- banyak `reduceRegion()` terpisah;
- agregasi bersamaan dalam jumlah besar;
- pencetakan list atau tabel besar;
- skala yang jauh lebih halus daripada sumber;
- komputasi 11 tahun pada setiap klik;
- `getInfo()` pada objek besar;
- `reproject()` tanpa kebutuhan yang terbukti.

### 9.3 Pola wajib

- filter tanggal dan AOI sedini mungkin;
- pilih band sebelum `map`;
- gunakan reducer gabungan dengan `sharedInputs`;
- benchmark `tileScale`;
- benchmark `parallelScale` ketika relevan;
- gunakan batch export untuk pekerjaan berat;
- gunakan aset turunan sebagai cache;
- catat jumlah citra, luas AOI, scale, durasi, status task, error, dan EECU jika tersedia.

Memory error tidak boleh “diperbaiki” hanya dengan menaikkan `maxPixels`. Penyebab algoritmik harus dianalisis.

---

## 10. Keamanan, autentikasi, dan approval

### 10.1 Rahasia

Codex dilarang:

- meminta password melalui chat;
- membaca file kredensial;
- membuka atau mencetak token;
- menampilkan environment variable rahasia;
- menulis rahasia ke source code, config, test fixture, log, atau dokumentasi;
- memasukkan kredensial ke Git;
- membuat service-account key tanpa persetujuan.

Kredensial Copernicus Marine dan Earth Engine harus disiapkan pengguna melalui mekanisme login resmi pada komputer lokal.

Codex boleh menjalankan CLI/API yang menggunakan sesi autentikasi lokal, tetapi tidak boleh membaca isi kredensialnya.

### 10.2 Operasi yang boleh dilakukan sebagai pekerjaan lokal aman

Jika kebijakan sandbox/approval Codex mengizinkan:

- membaca file proyek;
- mencari kode;
- memeriksa `git status` dan `git diff`;
- mengedit file dalam repository;
- menjalankan unit test;
- menjalankan lint dan type check;
- membuat output sintetis di direktori test/output;
- memeriksa metadata lokal yang tidak rahasia.

### 10.3 Operasi yang membutuhkan approval pengguna

Sebelum menjalankan, Codex harus meminta persetujuan atau menggunakan approval platform:

- autentikasi/login;
- akses jaringan;
- unduhan data nyata;
- instalasi atau upgrade dependency;
- perubahan Google Cloud Project;
- pembuatan atau perubahan IAM;
- upload Earth Engine Assets;
- penghapusan aset atau data;
- eksekusi batch skala penuh;
- aktivasi `daily_full`;
- penggunaan layanan Cloud berbayar;
- force push, reset, clean, atau operasi Git destruktif;
- perubahan keamanan atau approval mode.

Codex tidak boleh menonaktifkan sandbox, approval, atau kontrol keamanan agar tugas lebih mudah.

### 10.4 Penghapusan

Jangan menghapus:

- data mentah;
- file karantina;
- inventory;
- checksum;
- log validasi;
- metadata snapshot;
- aset GEE;

tanpa persetujuan eksplisit dan bukti backup atau regenerasi.

---

## 11. Aturan data dan provenance

Setiap file atau aset harus dapat ditelusuri ke:

- Product ID;
- Dataset ID;
- dataset version;
- dataset part;
- variabel;
- AOI;
- waktu;
- depth;
- versi Toolbox;
- versi pipeline;
- config hash;
- source checksum;
- timestamp pemrosesan;
- status validasi.

### 11.1 Nilai hilang dan mask

- `_FillValue` tidak boleh berubah menjadi nol;
- nol yang valid tidak boleh dimask;
- raw encoding dan CF-decoded values harus dibedakan;
- mask harus dipertahankan selama konversi;
- penerapan `scale_factor` dan `add_offset` dua kali dilarang.

### 11.2 Waktu

- waktu produk dipertahankan;
- WIT hanya untuk tampilan jika dibutuhkan;
- jangan menggeser timestamp sumber secara diam-diam;
- akhir periode GEE bersifat eksklusif;
- jumlah timestep harus diuji, termasuk tahun kabisat.

### 11.3 Versi dataset

Jangan mencampur dataset version atau dataset part dalam satu seri tanpa keputusan tertulis.

---

## 12. Struktur repository yang diharapkan

```text
glorys-current-lab/
├── AGENTS.md
├── PRD.md
├── README.md
├── CHANGELOG.md
├── pyproject.toml
├── requirements.txt
├── requirements-lock.txt
├── config/
├── python/
│   ├── common/
│   ├── metadata/
│   ├── download/
│   ├── validation/
│   ├── conversion/
│   ├── analytics/
│   ├── upload/
│   └── reporting/
├── gee/
│   ├── lib/
│   ├── analysis/
│   ├── vector/
│   ├── app/
│   └── tests/
├── docs/
│   ├── stages/
│   ├── adr/
│   ├── methodology/
│   ├── validation/
│   └── teaching/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── synthetic/
├── data/
│   ├── raw/
│   ├── validated/
│   ├── converted/
│   ├── partial/
│   └── quarantine/
└── outputs/
```

Codex tidak boleh memindahkan struktur besar tanpa ADR dan persetujuan.

Data besar, kredensial, output sementara, dan file lokal harus dikecualikan dari Git.

---

## 13. Standar implementasi Python

Kode Python wajib:

- runnable;
- modular;
- menggunakan type hints;
- memiliki docstring untuk fungsi publik;
- menggunakan `pathlib`;
- menggunakan logging, bukan hanya `print`;
- memiliki error handling;
- menggunakan config terpisah;
- memvalidasi input;
- menggunakan UTC untuk log/provenance;
- dapat dilanjutkan bila proses terputus;
- menghasilkan keluaran deterministik sejauh mungkin;
- menjaga file sumber tetap tidak berubah;
- menulis ke temporary file sebelum atomic move jika relevan.

### 13.1 Dependency

- gunakan dependency yang sudah dikunci;
- jangan upgrade diam-diam;
- dependency baru membutuhkan alasan dan approval;
- setelah perubahan dependency, ulangi test pilot yang relevan;
- perbarui `requirements-lock.txt` dan changelog.

### 13.2 Format dan quality gate

Gunakan konfigurasi repository yang tersedia untuk:

- formatter;
- lint;
- type checking;
- unit tests;
- integration tests.

Jangan mengarang command. Temukan command resmi dari `pyproject.toml`, README, Makefile, atau CI.

---

## 14. Standar implementasi GEE JavaScript

Kode GEE wajib:

- modular;
- tidak menaruh Asset ID tersebar di banyak file;
- membaca Project ID dan asset root dari konfigurasi;
- menggunakan nama band konsisten;
- menggunakan server-side objects dengan benar;
- membatasi penggunaan client-side operations;
- menyimpan metadata pada layer/output;
- menampilkan keterbatasan ilmiah;
- memisahkan fungsi interaktif, batch, dan pembaca produk prahitung;
- memiliki test arah kardinal;
- memiliki benchmark untuk fungsi yang dinyatakan interaktif.

Jangan mengandalkan `Map.addLayer()` sebagai bukti bahwa hasil ilmiah benar.

---

## 15. Pengujian wajib

### 15.1 Unit tests

Minimal:

- perhitungan jumlah periode;
- leap year;
- speed;
- mean speed;
- resultant speed;
- persistence;
- direction;
- pembagian nol;
- naming;
- config validation;
- inventory state transitions;
- checksum.

### 15.2 Synthetic tests

Minimal:

- empat vektor kardinal;
- zero speed;
- reversed latitude;
- `_FillValue`;
- scale/offset;
- mask;
- missing timestep;
- band tertukar;
- timestamp salah;
- depth mismatch.

### 15.3 Integration tests

Minimal:

- `describe` metadata;
- subset pilot;
- buka NetCDF;
- validasi NetCDF;
- konversi satu timestep;
- NetCDF–GeoTIFF comparison;
- upload sampel GEE;
- Python–GEE comparison.

### 15.4 Regression tests

Setiap perbaikan bug harus menambah test yang gagal sebelum perbaikan dan lulus setelah perbaikan.

### 15.5 Bukti

Test dianggap lulus hanya jika tersedia:

- command;
- exit status;
- ringkasan hasil;
- lokasi report/log;
- versi dependency;
- commit atau diff terkait.

Codex dilarang menulis “PASS” berdasarkan inspeksi visual semata.

---

## 16. Workflow Codex untuk setiap tugas

### 16.1 Sebelum mengubah kode

Codex harus:

1. membaca sumber relevan;
2. mengidentifikasi tahap aktif;
3. menemukan requirement ID;
4. memeriksa status implementasi;
5. memeriksa file dan tests terkait;
6. menyatakan asumsi;
7. memastikan operasi tidak membutuhkan approval tambahan.

### 16.2 Saat mengubah kode

Codex harus:

- membuat perubahan minimum yang lengkap;
- menjaga backward compatibility;
- tidak mengubah keputusan ilmiah tanpa ADR;
- menambahkan atau memperbarui tests;
- memperbarui dokumentasi yang terdampak;
- tidak memperbaiki masalah yang tidak terkait kecuali diperlukan untuk keselamatan atau test.

### 16.3 Setelah mengubah kode

Codex harus:

1. menjalankan test relevan;
2. menjalankan lint/type check yang relevan;
3. memeriksa diff;
4. memperbarui `docs/IMPLEMENTATION_STATUS.md`;
5. memperbarui `docs/REQUIREMENTS_TRACEABILITY.md`;
6. memperbarui `CHANGELOG.md`;
7. melaporkan file yang berubah;
8. melaporkan test yang dijalankan;
9. menyatakan keterbatasan dan pekerjaan tersisa;
10. tidak menyatakan tahap lulus jika acceptance criteria belum lengkap.

---

## 17. Requirement traceability

Codex wajib memelihara:

```text
docs/REQUIREMENTS_TRACEABILITY.md
```

Kolom minimum:

```text
requirement_id
description
stage
implementation_file
test_file
status
evidence
notes
```

Setiap perubahan harus dapat ditautkan ke requirement PRD atau technical requirement yang disetujui.

Jika pekerjaan tidak memiliki requirement:

- jangan langsung mengimplementasikan;
- dokumentasikan kebutuhan;
- tambahkan requirement melalui perubahan PRD/backlog yang disetujui.

---

## 18. ADR dan perubahan keputusan besar

ADR diperlukan untuk perubahan seperti:

- mengganti arsitektur Python–GEE;
- mengganti granularitas file;
- mengaktifkan data harian penuh;
- menambah kedalaman;
- mengganti dataset utama;
- mengubah definisi statistik;
- mengubah struktur aset;
- menambah backend/server;
- mengubah kebijakan autentikasi;
- menggunakan service account;
- mengubah batas komputasi interaktif.

Format ADR minimum:

```text
Context
Decision
Alternatives
Scientific impact
Technical impact
Security/cost impact
Validation required
Status
```

Codex boleh membuat draft ADR, tetapi tidak boleh menganggapnya diterima tanpa persetujuan.

---

## 19. Dokumentasi dan gaya bahasa

- Dokumentasi utama menggunakan Bahasa Indonesia.
- Nama variabel, API, dan istilah teknis boleh menggunakan bahasa aslinya.
- Definisikan istilah untuk pembaca pemula.
- Jangan menggunakan bahasa hiperbolik.
- Jangan menyembunyikan keterbatasan.
- Gunakan istilah:
  - “rata-rata besar kecepatan”;
  - “kecepatan resultan”;
  - “arah resultan”;
  - “arus dekat permukaan pada lapisan model teratas”;
  - “maksimum kecepatan arus rata-rata harian”.
- Jangan menggunakan istilah “akurasi tinggi” tanpa ukuran dan validasi.

---

## 20. Pelaporan hasil kerja

Setiap laporan Codex harus menyebut:

1. tahap aktif;
2. requirement ID;
3. tujuan perubahan;
4. file yang diubah;
5. keputusan ilmiah/teknis;
6. tests yang dijalankan;
7. hasil tests;
8. bukti yang dihasilkan;
9. risiko atau keterbatasan;
10. status berikutnya.

Format ringkas:

```markdown
## Ringkasan
- Tahap:
- Requirement:
- Perubahan:

## Validasi
- Command:
- Hasil:
- Bukti:

## Status
- PASS / PASS_WITH_NOTES / BLOCKED / FAIL
- Pekerjaan berikutnya:
```

---

## 21. Kondisi penghentian wajib

Codex harus berhenti dan melaporkan masalah jika ditemukan:

- Product ID atau Dataset ID tidak cocok;
- metadata berubah material;
- depth target tidak tersedia;
- satuan tidak diketahui;
- `uo` atau `vo` hilang;
- band tertukar;
- waktu hilang atau salah;
- jumlah timestep tidak cocok;
- `_FillValue` menjadi nol;
- lintang terbalik;
- CRS/transform salah;
- checksum mismatch;
- dataset version tercampur;
- arah kardinal gagal;
- nilai Python dan GEE tidak cocok dalam toleransi;
- memory error pada fitur yang diklaim interaktif;
- rahasia muncul dalam file atau log;
- tujuan penggunaan berubah menjadi operasional atau komersial;
- perubahan memerlukan layanan berbayar yang belum disetujui.

Fail closed lebih penting daripada melanjutkan dengan asumsi.

---

## 22. Definition of Done repository

MVP belum selesai sampai:

1. Tahap 0–10 lulus.
2. Semua requirement inti memiliki traceability.
3. Data inti dapat ditelusuri.
4. Produk prahitung tersedia.
5. Nilai Python, GeoTIFF, dan GEE konsisten.
6. Uji arah kardinal lulus.
7. Fitur interaktif lulus benchmark tanpa memory error.
8. Komputasi berat diarahkan ke Python atau batch.
9. GEE App menampilkan metadata dan keterbatasan.
10. Tests dan dokumentasi lengkap.
11. Tidak ada kredensial di repository.
12. Penggunaan nonkomersial terdokumentasi.
13. Tidak ada klaim ketelitian lokal palsu.
14. Tidak ada tahap yang dinyatakan lulus tanpa bukti.

---

## 23. Catatan untuk pengelola repository

Codex membaca instruksi proyek dari root menuju direktori kerja. Jika instruksi root menjadi terlalu besar atau modul memerlukan aturan khusus, gunakan `AGENTS.md` yang lebih dekat pada direktori, misalnya:

```text
python/validation/AGENTS.md
gee/app/AGENTS.md
```

Instruksi yang lebih dekat hanya boleh memperjelas atau memperketat aturan, bukan meniadakan prinsip ilmiah, keamanan, dan gerbang proyek tanpa persetujuan.
