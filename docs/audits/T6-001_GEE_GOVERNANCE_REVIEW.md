# T6-001 — Review Governance Google Earth Engine

- Tanggal audit: 2026-08-06 (Asia/Tokyo)
- Task ID: `T6-001`
- Scope: review read-only Project ID, tier, IAM, asset root, biaya/quota,
  dan batas approval sebelum publikasi aset Tahap 6.
- Mode: audit dokumentasi dan pemeriksaan lokal/offline.
- Keputusan: `PASS_WITH_NOTES`

## Batas operasi

Audit ini tidak melakukan login, `ee.Initialize()`, akses browser, pembacaan
credential/token/cookie, network, upload, export, delete, perubahan ACL/IAM,
atau start task cloud. Earth Engine runtime dan state Cloud aktif tidak
dianggap terverifikasi hanya karena konfigurasi lokal atau laporan pengguna
memuat nilai yang sama.

## Klasifikasi temuan

| Area | Status | Temuan | Kelas evidence |
|---|---|---|---|
| Project ID | `USER-REPORTED` + konsisten lokal | `ee-rahal13001` dilaporkan pengguna; konfigurasi lokal memuat ID yang sama | User-reported; repository-observed |
| Registrasi/purpose | `USER-REPORTED` | Registrasi Earth Engine nonkomersial dan tujuan pendidikan/penelitian dilaporkan pengguna | User-reported |
| Tier Earth Engine | `NOT_VERIFIED` | Tier aktif dan tanggal verifikasi tidak tersedia sebagai evidence independen | Not verified |
| IAM | `USER-REPORTED`; least privilege `NOT_VERIFIED` | FND-010 mencatat role `Owner` menurut review pengguna; kecukupan dan least privilege belum diaudit independen | User-reported; not verified |
| Asset root | `REPOSITORY-OBSERVED` untuk konfigurasi; live root `NOT_VERIFIED` | `projects/ee-rahal13001/assets/glorys_current`; prefix cocok dengan Project ID lokal | Repository-observed; live Cloud state not verified |
| ACL/private default | `NOT_VERIFIED` | Tidak ada review ACL live pada audit ini | Not verified |
| Billing | `USER-REPORTED` | FND-010 mencatat tidak ada billing account tertaut pada review pengguna 2026-08-03; ini tidak membuktikan tier aktif | User-reported |
| Quota/EECU/tasks | `USER-REPORTED` | FND-010 mencatat EECU `0`, quota view `0`, dan active tasks `0` pada 2026-08-03 | User-reported |
| Cloud services/resource inventory | `USER-REPORTED` | FND-010 mencatat resource report 6 record; cakupan dan kelengkapan tidak diaudit independen | User-reported |
| Browser/runtime | `NOT_USED` | Tidak ada browser atau Earth Engine runtime yang digunakan | Not verified |

## Kategori audit eksplisit

- **Repository-observed:** file konfigurasi, backlog, status, traceability,
  script GEE, dan evidence lokal yang tercantum di atas.
- **Independently verified:** hanya konsistensi lokal Project ID dengan asset
  root/prefix melalui pemeriksaan Python stdlib dan keberadaan/isi minimum
  dokumen audit melalui pemeriksaan offline. Ini bukan verifikasi Cloud.
- **User-reported:** registrasi, tier nonkomersial, IAM `Owner`, billing,
  EECU/quota/tasks, resource inventory, dan visibilitas asset yang tercatat di
  FND-009/FND-010 atau evidence terkait.
- **Browser-observed:** tidak ada; browser tidak digunakan.
- **Not verified/blocked:** live tier, least-privilege IAM, asset root/ACL,
  billing/quota limits aktif, dan Earth Engine runtime.

## Evidence repository

- `config/local.example.json` — Project ID dan asset root contoh.
- `config/asset_naming.json` — prefix, collection paths, dan pola nama aset.
- `python/common/config_loader.py` — guard lokal bahwa asset root mengikuti
  `projects/<project_id>/assets/`.
- `outputs/evidence/foundation/FND-009_governance_record.md` — governance
  user-reported dan daftar hal yang belum diaudit.
- `outputs/evidence/foundation/FND-010_cost_monitoring_plan.md` — review
  user-managed IAM, billing, EECU, quota, task, dan resource inventory.
- `outputs/evidence/foundation/FND-007_setup_report.md` — setup/auth boundary;
  tidak digunakan sebagai bukti independen Cloud.
- `docs/architecture_manifest.md` — asset boundary desain offline; bukan bukti
  asset live.
- `docs/audits/WP5-5_STATUS_RECONCILIATION.md` — dependency T5-028 dan batas
  transisi ke T6.

## Commands and exit status

Semua command berikut dijalankan pada 2026-08-06 (Asia/Tokyo), tanpa membaca
credential atau menghubungi layanan eksternal.

| Command | Exit | Evidence/limitation |
|---|---:|---|
| `git status --short --branch` | `0` | Branch `main`; worktree memiliki perubahan pengguna yang sudah ada. |
| `git log --oneline -5` | `0` | HEAD `5dd297a`; riwayat lokal terbaca. |
| `git rev-list --left-right --count HEAD...origin/main` | `0` | Output `0 0` terhadap ref lokal `origin/main`; bukan network fetch. |
| Pemeriksaan Python stdlib atas `config/local.example.json` dan `config/asset_naming.json` | `0` | Project ID sama, asset root sama, dan `projects/<id>/assets/glorys_current` cocok. |
| `graphify query "What is the current status of T6-001 through T6-014 and the active stage?" --budget 1800` | `0` | Graph repository memetakan status/dokumen; bukan validasi Cloud. |
| `graphify query "What dependencies connect T5 completion or evidence to T6 tasks?" --budget 1800` | `0` | Graph memetakan evidence T5; bukan approval transisi. |
| `graphify query "What existing GEE assets, asset IDs, GEE scripts, upload scripts, or dry-run mechanisms exist?" --budget 1800` | `0` | Graph memetakan file/script lokal; tidak menjalankan script GEE. |
| `graphify query "What governance evidence, audit reports, status records, and traceability documents exist for GEE or T6?" --budget 1800` | `0` | Graph memetakan evidence lokal; tidak mengaudit runtime/ACL/IAM. |
| `graphify update . --no-cluster` | `0` | Refresh AST/code-only offline setelah perubahan repository; file dokumen tidak diekstrak semantic. |
| `graphify cluster-only . --no-viz --no-label` | `0` | Graph lokal diperbarui menjadi 1.030 node, 2.013 edge, dan 84 komunitas; tidak ada backend eksternal. |

`git diff --check` tidak dipakai sebagai gate T6-001 karena worktree memiliki
perubahan pengguna yang luas dan beberapa file historis dengan trailing
whitespace. Hal tersebut tidak mengubah hasil governance review.

## Checklist acceptance T6-001

- [x] Project ID memiliki sumber evidence yang jelas: konfigurasi lokal dan
  laporan user-managed FND-009/FND-010.
- [x] Tier dicatat sebagai `NOT_VERIFIED` karena tidak ada audit independen.
- [x] IAM dicatat sebagai user-reported `Owner`; least privilege tetap
  `NOT_VERIFIED`.
- [x] Asset root dan prefix project diperiksa secara lokal; live existence,
  ownership, dan ACL belum diverifikasi.
- [x] Batas biaya/EECU/quota dicatat dari FND-010 sebagai user-reported; exact
  tier dan limit aktif belum diverifikasi.
- [x] Tidak ada credential yang dibaca.
- [x] Tidak ada upload atau task cloud yang dijalankan.
- [x] Command, exit status, evidence, timestamp, dan limitation dicatat.
- [x] User-managed dibedakan dari repository-observed dan independently
  verified.
- [x] Rekomendasi T6-002 dan T6-003 tersedia di bawah.

## Rekomendasi T6-002 dan T6-003

T6-002 sebaiknya memfinalkan schema source asset dengan properti wajib yang
menjaga identitas dataset, `uo`/`vo`, unit `m s-1`, depth `0.494025 m`, label
lapisan model teratas, timestamp end-exclusive, period type, CRS/grid/mask,
source file/checksum, dataset version/part, pipeline/config hash, dan
provenance. Schema harus tetap membedakan monthly dan daily JFM; `daily_full`
tetap nonaktif.

T6-003 sebaiknya memfinalkan schema derived asset dengan identitas produk,
source manifest/checksum, frame/reference period, method/formula atau
analytics version, unit, depth, mask checksum, CRS/grid, dan limitation.
Derived asset tidak boleh dipublikasikan hanya karena tersedia lokal; daftar
produk tetap harus dipilih berdasarkan kebutuhan App/teaching/research dan
approval publikasi berikutnya.

Kedua rekomendasi tersebut adalah input desain, bukan persetujuan upload atau
perubahan keputusan ilmiah.

## Approval dan pekerjaan yang masih diperlukan

Sebelum T6-005, T6-009, atau T6-010 diperlukan approval eksplisit untuk operasi
cloud serta verifikasi user-managed terhadap tier, IAM/least privilege, live
asset root, ACL private default, quota/EECU, dan batas biaya. T6-001 tidak
memberi otorisasi untuk operasi tersebut. T6-002 dan T6-003 masih merupakan
pekerjaan berikutnya; T6-004 dan seluruh task upload tetap `NOT_STARTED`.

## Status akhir

`PASS_WITH_NOTES` — identitas Project ID dan prefix asset root konsisten pada
repository, dan evidence user-managed governance tersedia. Tier, least
privilege IAM, live asset state, ACL, serta quota/billing limits independen
belum terverifikasi. Tidak ada operasi cloud dilakukan.
