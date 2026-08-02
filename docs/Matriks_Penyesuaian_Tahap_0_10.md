# MATRIKS PENYESUAIAN TAHAP GLORYS12V1

**Tanggal:** 31 Juli 2026  
**Alasan:** Penetapan penggunaan khusus pendidikan dan penelitian nonkomersial serta penerapan arsitektur hibrida Python–GEE.

---

## 1. Kesimpulan

Tahap 0–3 tidak perlu dibatalkan. Struktur ilmiah dan data yang telah dibuat tetap berlaku.

Penyesuaian diperlukan pada:

- klasifikasi penggunaan;
- pembagian komputasi;
- benchmark;
- produk prahitung;
- tata kelola Earth Engine;
- kriteria penerimaan.

---

## 2. Dampak per tahap

| Tahap | Tingkat perubahan | Keputusan |
|---|---|---|
| 0 | Kecil | tambah klasifikasi nonkomersial dan governance |
| 1 | Besar | tetapkan arsitektur hibrida dan guardrail GEE |
| 2 | Besar | tambah benchmark memory, EECU, interactive/batch/Python |
| 3 | Kecil–sedang | tambah provenance dan manifest downstream |
| 4 | Sedang | validasi menjadi dasar komputasi Python |
| 5 | Besar | konversi plus produk prahitung |
| 6 | Sedang | publish-on-demand |
| 7 | Besar | pisahkan modul interaktif, batch, precomputed |
| 8 | Kecil | visualisasi tetap, tetapi memakai produk tervalidasi |
| 9 | Besar | App tidak menghitung ulang 11 tahun |
| 10 | Sedang | validasi ilmiah plus performa dan governance |

---

## 3. Hal yang tidak berubah

- Product ID;
- Dataset ID;
- `uo` dan `vo`;
- satuan;
- kedalaman 0,494025 m;
- periode 2015–2025;
- 11 tahun;
- 132 bulanan;
- 993 harian JFM;
- formula speed;
- formula resultan;
- arah menuju;
- persistensi;
- keterbatasan reanalisis;
- keterbatasan pasang surut.

---

## 4. Hal yang berubah

### Sebelum

```text
Copernicus → Python → GeoTIFF → GEE → seluruh analisis
```

### Sesudah

```text
Copernicus
  → Python validation
  → Python heavy analytics
  → precomputed products
  → GEE source + derived assets
  → limited interactive analysis
```

---

## 5. Keputusan kelanjutan

Dokumen baseline:

1. Tahap 0 v1.1
2. Tahap 1 v1.1
3. Tahap 2 v1.1
4. Tahap 3 v1.1
5. PRD GLORYS Current Lab v1.0

Versi sebelumnya tetap disimpan sebagai histori, tetapi Codex menggunakan versi terbaru.
