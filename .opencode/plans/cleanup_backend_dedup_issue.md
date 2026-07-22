# Cleanup — Duplikasi & Abstraksi Belum Terpakai (Backend)

## Status
Technical debt — dikerjakan sebelum 16.5 agar fondasi bersih.

## Prinsip
Beres-beres kode existing, BUKAN fitur baru. Perilaku & format endpoint dari
sisi user harus SAMA PERSIS. Tidak ada perubahan arsitektur besar.

## Temuan (audit kode)
1. **Rate limiter ganda.** Dua mekanisme: `RequestScheduler` (configurable via
   `settings.rate_limit_per_minute`, shared antar-provider) DAN `_rate_limit()`
   sederhana (interval fixed 1.0s, global lock) yang DIDUPLIKASI di `base.py`
   (Yahoo) & `idx_provider.py` (IDX). Untuk idx/stock keduanya jalan berbarengan.
2. **CacheBackend abstrak belum terpakai.** `cache/__init__.py` punya ABC
   `CacheBackend` dengan hanya 1 implementasi nyata (`MemoryCache`).
3. **BaseService bawa 4 dependency.** `services/base.py` `BaseService` inject 4
   repo, padahal tiap service cuma pakai 1.
4. **Dua HTTP client.** `curl_cffi` (anti-block) dipakai luas; `requests` (umum)
   cuma di `data/ticker_sync.py` untuk Sectors.app.

## Langkah High-Level
1. **Satukan rate limiter → `RequestScheduler` saja.** Semua provider (Yahoo &
   IDX) pakai `await request_scheduler.acquire()`. Hapus `_rate_limit()` +
   variabel pendukungnya di `base.py` & `idx_provider.py`. Jaga agar rate TIDAK
   jadi lebih cepat dari sebelumnya (efektif ~60/menit) — sesuaikan default
   config bila perlu.
2. **Buang `CacheBackend`.** `CacheService` & `MemoryCache` tanpa ABC. Fungsi
   cache (set/get/delete/clear per kategori + TTL) tetap sama.
3. **Pangkas `BaseService`.** Tiap service pegang HANYA repo yang dipakai.
   `validate_ticker` tetap fungsi biasa. Hapus `BaseService` bila tak ada lagi
   yang diwariskan.
4. **Satukan HTTP client.** Sectors.app tak butuh anti-block, tapi konversi ke
   `curl_cffi` supaya kode backend hanya pakai satu library HTTP.

## Batasan
- Backend ONLY. Tidak ubah frontend / skema / format response.
- Tidak tambah fitur/dependency baru; tidak ada dead code/import tersisa.
- Tidak ada penurunan performa / peningkatan jumlah request ke provider.

## Verifikasi
- Smoke test existing (`test_providers_smoke.py`, `test_16_4_7_validation.py`)
  tetap lolos.
- Manual: data Yahoo & IDX beberapa ticker SAMA seperti sebelum (tidak ada yang
  hilang/gagal baru).
- Cache: set/get tiap kategori (profil, fundamental, berita, harga) normal.
- Import bersih, tak ada dependency jadi tak terpakai.
- Laporan ringkas apa yang dihapus/disederhanakan.

## Deliverable
- Branch `feat/cleanup-backend-dedup` dari `main`.
- PR ke `main`, JANGAN di-merge (untuk ditinjau).
- Issue GitHub berisi plan ini.
