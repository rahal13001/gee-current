# ADR-006 — Daily Full Nonaktif

- Status: `PROPOSED` (diwarisi dari PRD)
- Context: Data harian penuh 2015–2025 bukan kebutuhan MVP.
- Decision: `daily_full` nonaktif secara default.
- Alternatives: aktivasi hanya melalui approval gate dan change control.
- Scientific impact: tidak mengubah data inti.
- Technical impact: guardrail konfigurasi wajib fail closed.
- Security/cost impact: menghindari download/compute yang tidak disetujui.
- Validation required: konfigurasi harus menguji default off.
