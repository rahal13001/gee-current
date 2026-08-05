# Panduan Operasional Python dan PowerShell

Panduan ini menjelaskan cara menjalankan pekerjaan lokal GLORYS12V1, mengubah
AOI, mengubah rentang waktu, dan menyiapkan pemeriksaan sebelum operasi GEE.
Panduan ini tidak mengubah keputusan ilmiah, status milestone, atau status ADR.

## 1. Konvensi proyek

Jalankan semua command dari root repository:

```powershell
Set-Location E:\project\gee-current
```

Gunakan interpreter repository secara eksplisit agar dependency tidak tertukar:

```powershell
$PyExe = ".\.venv\Scripts\python.exe"
& $PyExe --version
& $PyExe -m pip check
```

Baseline yang disetujui user adalah Python `3.12.13`, `earthengine-api==1.7.37`,
dan `copernicusmarine==2.4.1`. Jangan menjalankan `pip install`, upgrade, atau
uninstall sebagai bagian dari prosedur rutin.

Autentikasi tetap dikelola user. Panduan ini tidak meminta, membaca, atau
menampilkan credential, token, cookie, atau environment variable rahasia.

## 2. File konfigurasi yang boleh diubah

Kode tidak perlu diubah ketika hanya AOI atau waktu analisis yang berubah.
Gunakan file berikut:

| Kebutuhan | File |
|---|---|
| AOI bbox | `config/study_area.json` |
| Periode penuh dan JFM | `config/analysis_period.json` |
| Project dan asset root lokal | `config/local.example.json` atau konfigurasi lokal yang disetujui |
| Pola nama asset | `config/asset_naming.json` |
| Kedalaman | `config/depth_selection.json` |

Salin nilai contoh dengan hati-hati dan edit melalui editor. Jangan menulis
file konfigurasi menggunakan redirection, `Set-Content`, atau Python write
trick.

## 3. Cara menulis dan mengubah AOI

### 3.1 Arti koordinat

Di konfigurasi proyek, `west` dan `east` adalah batas barat dan timur, bukan
indikator hemisfer. AOI aktif regional Indonesia Timur berada pada bujur timur,
sehingga nilainya positif. Konfigurasi `pilot_001` tetap tersedia terpisah untuk T2:

```json
{
  "west": 122.986190,
  "east": 143.326183,
  "south": -12.191592,
  "north": 4.265137,
  "crs": "EPSG:4326"
}
```

Aturannya:

- bujur barat ditulis pada `west`;
- bujur timur ditulis pada `east`;
- lintang selatan ditulis pada `south`;
- lintang utara ditulis pada `north`;
- `west < east` dan `south < north` wajib benar;
- rentang bujur berada pada `-180..180` dan lintang pada `-90..90`;
- urutan koordinat Earth Engine adalah `[west, south, east, north]`.

Jangan mengubah tanda bujur hanya karena labelnya `W`. Untuk AOI Papua pada
repository ini, `W` berarti western boundary dan tetap bernilai `129.199367`
derajat bujur timur.

### 3.2 Membuat AOI di Python

Contoh berikut membaca konfigurasi, memvalidasi urutan bbox, lalu membuat
geometri Earth Engine. Baris `ee.Initialize` hanya dijalankan pada sesi online
yang memang sudah disetujui user; tidak diperlukan untuk pemeriksaan JSON lokal.

```python
import json
from pathlib import Path

import ee

ROOT = Path(__file__).resolve().parents[1]
with (ROOT / "config" / "study_area.json").open(encoding="utf-8") as handle:
    aoi_config = json.load(handle)

west = float(aoi_config["west"])
east = float(aoi_config["east"])
south = float(aoi_config["south"])
north = float(aoi_config["north"])

if not west < east:
    raise ValueError("west harus lebih kecil daripada east")
if not south < north:
    raise ValueError("south harus lebih kecil daripada north")

# Earth Engine: west, south, east, north.
aoi = ee.Geometry.Rectangle(
    [west, south, east, north],
    proj="EPSG:4326",
    geodesic=False,
)
```

AOI dapat berubah pada tahap berikutnya. Setiap perubahan harus dicatat sebagai
konfigurasi baru atau perubahan terdokumentasi, lalu pilot dan statistik AOI
diulang. Jangan mengganti AOI di tengah perbandingan tanpa mencatat versinya.

## 4. Cara mengubah rentang waktu

Semua filter waktu Earth Engine bersifat **akhir eksklusif**. Pola yang benar:

```text
start = tanggal pertama yang ingin diambil
end   = tanggal setelah tanggal terakhir yang ingin diambil
```

Contoh:

| Tujuan | `start` | `end_exclusive` | Jumlah |
|---|---|---|---:|
| Februari 2020 | `2020-02-01` | `2020-03-01` | 29 |
| JFM 2020 | `2020-01-01` | `2020-04-01` | 91 |
| JFM 2021 | `2021-01-01` | `2021-04-01` | 90 |
| Periode penuh | `2015-01-01` | `2026-01-01` | 11 tahun |

Python:

```python
from datetime import date, timedelta

start = date.fromisoformat("2020-02-01")
last_day = date.fromisoformat("2020-02-29")
end_exclusive = last_day + timedelta(days=1)

if not start < end_exclusive:
    raise ValueError("start harus lebih awal daripada end_exclusive")
```

Untuk Earth Engine JavaScript atau Python API, gunakan `filterDate(start,
end_exclusive)`. Jangan memakai `2020-02-29` sebagai batas akhir jika tanggal
29 Februari harus ikut diambil.

## 5. Pemeriksaan konfigurasi dari PowerShell

Periksa konfigurasi tanpa autentikasi dan tanpa network:

```powershell
Set-Location E:\project\gee-current

$study = Get-Content .\config\study_area.json -Raw | ConvertFrom-Json
$period = Get-Content .\config\analysis_period.json -Raw | ConvertFrom-Json

[PSCustomObject]@{
  aoi_id = $study.aoi_id
  west = $study.west
  east = $study.east
  south = $study.south
  north = $study.north
  full_start = $period.full_period.start
  full_end_exclusive = $period.full_period.end_exclusive
  monthly_expected = $period.monthly_count_expected
  daily_jfm_expected = $period.daily_jfm_count_expected
}
```

Validasi dasar angka:

```powershell
if (-not ($study.west -lt $study.east)) { throw 'AOI west/east tidak valid' }
if (-not ($study.south -lt $study.north)) { throw 'AOI south/north tidak valid' }
if (($study.west -lt -180) -or ($study.east -gt 180)) { throw 'Bujur di luar batas' }
if (($study.south -lt -90) -or ($study.north -gt 90)) { throw 'Lintang di luar batas' }
```

## 6. Pemeriksaan dan konversi pilot lokal

Periksa jumlah GeoTIFF:

```powershell
$geotiffFiles = Get-ChildItem .\data\geotiff -Filter 'glorys12v1_daily_surface_202002*.tif'
$geotiffFiles.Count
```

Konversi NetCDF pilot menjadi 29 GeoTIFF tervalidasi:

```powershell
& .\.venv\Scripts\python.exe `
  .\tools\convert_t2_pilot_to_geotiff.py `
  --input .\data\raw\glorys12v1_daily_surface_20200201_20200229_pilot_retry.nc `
  --output-dir .\data\geotiff `
  --prefix glorys12v1_daily_surface `
  --overwrite
```

Band keluaran harus tetap `uo` dan `vo`, bertipe float32, CRS `EPSG:4326`,
resolusi sumber, dan nodata yang konsisten. Jangan melakukan resampling hanya
agar tampilan terlihat lebih halus.

Bandingkan GeoTIFF dengan NetCDF sumber:

```powershell
& .\.venv\Scripts\python.exe `
  .\tools\validate_t2_geotiff_against_netcdf.py `
  --netcdf .\data\raw\glorys12v1_daily_surface_20200201_20200229_pilot_retry.nc `
  --geotiff-dir .\data\geotiff `
  --prefix glorys12v1_daily_surface
```

Jika validasi gagal, berhenti dan perbaiki sumbernya. Jangan langsung mengubah
mask, urutan latitude, depth, unit, atau timestamp untuk membuat hasil lulus.

## 7. Menyiapkan plan unduhan Tahap 3

Builder plan hanya membaca konfigurasi lokal dan snapshot metadata yang sudah
disetujui. Mode `--dry-run` tidak menulis CSV, tidak login, dan tidak mengakses
network.

```powershell
Set-Location E:\project\gee-current

$PyExe = ".\.venv\Scripts\python.exe"
& $PyExe .\python\02_build_download_plan.py --plan monthly_all --dry-run
& $PyExe .\python\02_build_download_plan.py --plan daily_jfm --dry-run
```

Hasil yang diharapkan adalah 132 job bulanan, 33 job JFM, dan 993 expected
timesteps. `daily_full` harus tetap ditolak:

```powershell
& $PyExe .\python\02_build_download_plan.py --plan daily_full --dry-run
```

Jangan menjalankan download sebelum T2-025 lulus, plan ditinjau, dan user
memberikan approval operasional. Pembuatan CSV plan eksplisit, bila sudah
disetujui, menggunakan `--output` tanpa `--dry-run`.

Executor T3-014 memiliki guard opt-in. Setelah login Copernicus Marine valid,
metadata aktif diverifikasi, ruang penyimpanan mencukupi, dan user menyetujui
operasi jaringan, mode aktual bulanan dipanggil dengan:

```powershell
& $PyExe .\python\03_download_glorys.py `
  --plan monthly_all `
  --execute
```

Tanpa `--execute`, tidak ada request jaringan. `daily_full` tetap tidak boleh
dijalankan; `daily_jfm` adalah batch terpisah T3-015. Kedua batch boleh berbagi
SQLite inventory yang sama: executor hanya memvalidasi dan memproses job dari
plan aktif, sementara status plan lain dipertahankan.

## 8. Pola kerja Earth Engine setelah file siap

Operasi asset adalah operasi cloud dan dilakukan hanya setelah user menyetujui
target, periode, AOI, dan nama asset. Untuk setiap tanggal, catat:

- file sumber;
- asset ID;
- tanggal UTC;
- band `uo` dan `vo`;
- depth `0.494025 m`;
- unit `m s-1`;
- status task dan error jika ada.

Upload raw GeoTIFF tidak otomatis membuktikan bahwa band, timestamp, mask, dan
metadata sudah benar. Setelah upload, lakukan validasi read-only sebelum
statistik AOI atau benchmark.

Untuk pilot saat ini, jangan mengubah struktur temporal 29 tanggal menjadi satu
asset bertile. Setiap tanggal harus tetap dapat dibedakan sebagai image asset
atau item koleksi yang sesuai.

## 9. Urutan kerja yang disarankan

```text
ubah config
  -> validasi AOI dan periode secara offline
  -> validasi metadata aktif
  -> validasi NetCDF
  -> konversi GeoTIFF
  -> bandingkan NetCDF–GeoTIFF
  -> upload asset terpilih
  -> validasi asset GEE
  -> statistik AOI ringan
  -> bangun plan T3 secara dry-run
  -> benchmark B1–B3
```

Panduan ini dapat digunakan kembali ketika AOI atau rentang waktu berubah.
Perubahan konfigurasi tidak otomatis menaikkan status T0, T2, atau M1; setiap
gerbang tetap membutuhkan command, exit status, evidence, dan limitation.
