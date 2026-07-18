# Plan 16.4.1 — Data Layer Architecture

## Konteks (hasil audit kode yang sudah ada)

Sebelum menyusun rencana kerja, kode `backend/` sudah mengimplementasikan
**sebagian besar** scope 16.4.1. Audit singkat:

| Item scope 16.4.1            | Status saat ini                                             | Lokasi |
|------------------------------|-------------------------------------------------------------|--------|
| Provider Adapter             | ✅ Ada pattern `Provider` + `base.py` helper bersama        | `app/providers/` |
| Yahoo Finance Service        | ✅ `StockPriceProvider`, `CompanyProfileProvider`, `FundamentalsProvider`, `NewsProvider` | `app/providers/*.py` |
| News Provider (RSS)          | ⚠️ Baru Yahoo News, belum RSS terpisah                     | `app/providers/news_provider.py` |
| Repository Pattern           | ✅ 4 repository + instance default                          | `app/repositories/` |
| Standard Response Model      | ✅ `BaseService` + `AppError`/`ProviderError` error terpusat | `app/services/base.py`, `app/utils/errors.py` |
| Error Handling               | ✅ Error class terstruktur (`ProviderTimeoutError`, `RateLimitError`, `NetworkError`, dll) | `app/utils/errors.py` |
| Retry & Backoff              | ⚠️ Parsial: retry ada di `StockPriceProvider` (loop timeout + sleep), fallback mock; belum terstandarisasi sebagai helper di `base.py` | `app/providers/stock_price_provider.py`, `app/providers/base.py` |
| Async Request Scheduler      | ⚠️ Belum ada abstraksi "request scheduler"; `scheduler.py` hanya batch scan, bukan scheduler request/rate-limit terpusat | `app/scheduler.py` |
| Cache Interface              | ✅ `CacheBackend` (ABC) + `MemoryCache`                     | `app/cache/` |
| IDX API Service (Primary)    | ❌ Belum ada — dokumen masih tandai keputusan A/B **pending** | — |

**Kesimpulan:** 16.4.1 tidak mulai dari nol. Pekerjaan nyata adalah:
1. Menutup celah yang belum ada (IDX provider, request scheduler, RSS, retry helper).
2. Menyelesaikan keputusan A/B integrasi IDX yang *masih pending* di dokumen.
3. Menyamakan arsitektur agar konsisten (satu pola Provider/Repository untuk semua sumber).

---

## Keputusan yang harus diambil dulu (blocker)

Dokumen menandai integrasi IDX-API sebagai **pending (A vs B)**:

- **Opsi A** — Jalankan `NeaByteLab/IDX-API` (Deno/TS) sebagai service terpisah
  (cron sync → SQLite lokal), FastAPI baca SQLite hasil sync (read-only
  cross-process).
- **Opsi B** — Reimplement pemanggilan endpoint IDX langsung di Python.

Rekomendasi (butuh konfirmasi user): **Opsi B** untuk 16.4.1.
Alasan: stack sudah FastAPI/Python; memanggil endpoint IDX publik langsung
(lihat pola di `app/data/ticker_sync.py` yang sudah pakai `curl_cffi` +
header browser-like ke `idx.co.id`) menghindari dual-runtime (Deno + Python)
dan cron service terpisah. Kita buat `IdxProvider` yang mengikuti
`Provider` pattern yang sudah ada, sehingga tidak menambah infrastruktur.

Jika user memilih A, plan berubah jadi: buat `IdxSqliteRepository` yang baca
SQLite eksternal (read-only) + dokumentasikan cara jalankan sync Deno.

> ACTION: tanya user A atau B sebelum implementasi dimulai.

---

## Rencana Kerja (urutan eksekusi)

### Langkah 1 — Sepakati integrasi IDX (A/B)
- Tanya user. Default rekomendasi = B.
- Keluaran: satu kalimat keputusan yang dicatat di `Perbaikan_16.4_*.md`.

### Langkah 2 — Standarisasi Retry & Backoff helper di `base.py`
- Tambah `async def _retry(fn, retries, base_delay, backoff)` di
  `app/providers/base.py` (eksponensial backoff + respekt `RateLimitError`).
- Refactor `StockPriceProvider` untuk pakai helper ini (hapus loop timeout
  manual yang duplikat). Satu tempat = satu perilaku retry konsisten.
- Provider lain (profile, fundamentals, news) bisa pakai helper yang sama
  bila diinginkan (opsional, tidak wajib untuk 16.4.1).

### Langkah 3 — `IdxProvider` (Primary source)
Sesuai keputusan A/B (asumsi B):
- File baru `app/providers/idx_provider.py` dengan method:
  - `fetch_company_profile(symbol)` → profile (name, sector, industry, dll)
  - `fetch_fundamentals(symbol)` → financial ratio/report/dividend (lihat
    daftar field 16.4.3)
  - `fetch_daily_price(symbol)` → daily OHLCV (granularitas daily, bukan intraday)
- Ikuti pola `base.py`: rate-limit, `_run_yf`-like wrapper untuk HTTP call ke
  IDX, error mapping ke `ProviderError`, fallback aman (return dict dengan
  key `error` seperti provider lain, bukan raise).
- Daftarkan di `app/providers/__init__.py`.

### Langkah 4 — Async Request Scheduler (rate-limit terpusat)
- Buat `app/providers/scheduler.py` (atau `app/data/request_scheduler.py`)
  berisi:
  - Semaphore/global rate limiter berbasis `settings.rate_limit_per_minute`.
  - Fungsi `schedule(coro_factory)` yang antrikan request antar provider
    supaya batas rate tidak dilanggar (saat ini `_rate_limit` di `base.py`
    hanya jeda 1 detik antar call, belum batasi per-menit).
  - Reuse `_in_flight` dedup yang sudah ada di `base.py`.
- `StockPriceProvider` & `IdxProvider` pakai scheduler ini.
- Catatan: ini BUKAN scheduler batch scan (`scheduler.py` tetap untuk daily
  scan). Nama file berbeda supaya tidak tabrakan.

### Langkah 5 — News Provider RSS (secondary, raw only)
- Tambah `fetch_rss(symbol)` di `app/providers/news_provider.py` atau file
  baru `app/providers/rss_provider.py` yang baca Google News / IDX RSS.
- Hanya raw data (headline, publisher, published, summary, url, related
  ticker) — TIDAK ada sentiment label (itu di 16.8).
- Gabungkan dengan hasil Yahoo News di repository/news service bila perlu
  (bisa ditunda ke 16.4.4).

### Langkah 6 — Repository untuk IDX (bila perlu)
- Bila `IdxProvider` butuh cache terpisah, buat
  `app/repositories/idx_repository.py` mengikuti pola repository yang ada.
- Bila Opsi A dipilih, repository baca SQLite eksternal (read-only).

### Langkah 7 — Verifikasi arsitektur konsisten
- Pastikan semua entry point akses data lewat `Repository` → `Provider`,
  tidak ada modul yang panggil yfinance/HTTP langsung kecuali di provider.
- Pastikan `CacheBackend` dipakai semua repository (sudah, via `MemoryCache`).

---

## Yang TIDAK dikerjakan di 16.4.1 (ditunda ke stage lain)

- **Smart Cache TTL final** (7 hari / 24 jam / 1 jam / 5 menit / 1 menit) →
  16.4.5. Saat ini repository pakai TTL sementara (3600 detik dll). Biarkan,
  jangan ubah sekarang supaya tidak drift dengan 16.4.5.
- **Frontend Research Page** → 16.4.6.
- **Sentiment / News Category tagging** → 16.8 (bukan raw data).
- **Testing & Validation formal** → 16.4.7 (tapi lihat "Check" di bawah).

---

## Acceptance Criteria (16.4.1)

- [ ] Keputusan integrasi IDX (A/B) tercatat.
- [ ] Semua provider (Yahoo + IDX + RSS) pakai satu pola & helper `base.py`
      yang sama (rate-limit, retry/backoff, error mapping).
- [ ] Ada abstraksi Async Request Scheduler yang membatasi rate per menit.
- [ ] `CacheBackend` dipakai konsisten di semua repository.
- [ ] Tidak ada pemanggilan yfinance/HTTP di luar `app/providers/`.
- [ ] IDX provider mengembalikan data daily (bukan intraday); intraday tetap
      dari Yahoo (`fetch_history`).

## Check (minimal, tanpa framework)
- Tambah `test_providers_smoke.py` kecil yang:
  - import semua provider & repository tanpa error,
  - panggil `IdxProvider`/`StockPriceProvider` dengan mock/offline dan assert
    fallback mengembalikan dict `error` (bukan raise).
- Jalankan `python -m pytest test_providers_smoke.py -q` (atau cukup
  `python -c "import app.providers, app.repositories"`).

---

## File yang akan disentuh / dibuat

- Baru: `app/providers/idx_provider.py`, `app/providers/rss_provider.py`
  (atau method di `news_provider.py`), `app/providers/scheduler.py`,
  `app/repositories/idx_repository.py` (bila perlu), `test_providers_smoke.py`.
- Edit: `app/providers/base.py` (retry helper), `app/providers/__init__.py`
  (export), `app/providers/stock_price_provider.py` (pakai retry helper),
  `Perbaikan_16.4_*.md` (catat keputusan A/B).
- Tidak diubah: TTL cache (tunggu 16.4.5), frontend, service/router existing
  (kecuali perlu wiring `IdxProvider` — bisa ditunda ke 16.4.2/16.4.3).
