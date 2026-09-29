# Desain: Integrasi IDX Edge PRO sebagai Sumber Data

Tanggal: 2026-09-29
Status: Disetujui (menunggu review spec)
Pendekatan: A — Adapter provider baru + repository lama sebagai seam

## 1. Latar Belakang

Aplikasi (backend FastAPI + frontend Next.js) mengambil data pasar saham IDX
dari Yahoo Finance (yfinance) dan scraping idx.co.id. Kedua sumber sering
rate-limit dan tidak stabil.

`https://stock.arjum.com` ("IDX Edge PRO") menyediakan REST API saham IDX yang
stabil (13 endpoint resmi) dan MCP server. Tujuan Tahap 1: **memakai REST API
IDX Edge PRO sebagai sumber data utama untuk fitur yang sudah ada**, tanpa
mengubah perilaku aplikasi yang terlihat pengguna.

## 2. Fakta API (terverifikasi 2026-09-29)

- Base URL: `https://stock.arjum.com`
- Auth: header `X-API-Key` (atau Bearer). Endpoint data butuh key; `/api/health` publik.
- Kuota: `x-ratelimit-limit: 1000` (per hari), `x-ratelimit-remaining`.
- `market-cap`: `per_page` maks 50; total 963 emiten → ~20 request untuk semua.
- `search`: cocok untuk verifikasi ticker — kode tidak ada → `[]`.
- Hanya 13 endpoint resmi yang dibuka untuk API key. `/api/stocks`, `/api/realtime` → 403.

Endpoint resmi dan bentuk ringkas respons:

| Endpoint | Respons ringkas |
|---|---|
| `GET /api/health` | `{ok, status}` |
| `GET /api/search?q=` | `[{stock_code, stock_name, last_date, ...}]` |
| `GET /api/price/{code}` | `{code, last_price, freq, lot, value, market_state, ...}` |
| `GET /api/history/{code}?frame=daily&limit=N` | `{stock_code, frame, data_available, rows:[{date, open, high, low, close, volume, value, freq, change, change_pct, f_buy, f_sell, n_foreign, avg}]}` |
| `GET /api/analysis/{code}` | `{stock_code, output}` (teks) |
| `GET /api/screener/latest` | `{date, source, rows:[{stock_code, stock_name, bucket, summary, wr_event, potential, drawdown, note}], ...}` |
| `GET /api/broker-summary/{code}?start_date&end_date&flow&net&...` | `{stock_code, brokers:[{broker_code, broker_name, bval, bvol, ..., nval, nvol}], ...}` |
| `GET /api/broker-accumulation/{code}?...` | `{code, series:[...], top_buyers, top_sellers}` |
| `GET /api/seasonal/{code}` | `{stock_code, years, monthly_returns, summary, yearly_avg}` |
| `GET /api/market-cap?page&per_page&codes` | `{date, total, page, per_page, total_pages, data:[{code, name, close, listed_shares, market_cap, turnover_ratio, ...}]}` |
| `GET /api/financial-statements/{code}?...` | `{stock_code, report_type, period, count, items:[{year, quarter, label, data:{...}}]}` |
| `GET /api/insiders/{code}?...` | `{stock_code, count, total, page, items:[{name, date, action_type, ...}]}` |
| `GET /api/done-details?code&date&page&per_page` | `{code, date, total, page, per_page, data:[{time, price, lot, buyer, seller, action, ...}]}` |

## 3. Celah API (tidak ada endpoint)

API tidak menyediakan: **berita**, **profil perusahaan detail** (sector, industry,
website, business_summary), **rasio fundamental siap pakai** (PE/PBV/ROE/ROA/DER/
margin/dividend yield), **kalender earnings** dan **price target/rekomendasi analis**.

Keputusan: sumber lama (scraping idx.co.id + Yahoo + Google RSS) **dipertahankan
hanya untuk 4 celah ini**. Scraping IDX untuk harga dihapus.

## 4. Tujuan & Non-Tujuan

Tujuan (Tahap 1):
- Ganti sumber **harga/history**, **verifikasi ticker**, **sync daftar ticker**,
  dan **broker summary (Market Intelligence)** ke IDX Edge PRO.
- Ubah **alur screening** agar muat kuota 1000/hari.
- Pertahankan bentuk data & kontrak yang dikonsumsi `scoring`/`indicators`/`routers`
  agar UI tidak berubah.

Non-tujuan (ditunda ke fase berikutnya):
- Endpoint/UI fitur baru: analysis, screener vendor, akumulasi broker,
  seasonality, insider, order flow, market cap.
- Menghapus provider lama untuk celah (berita, profil, rasio, earnings/analyst).
- Integrasi MCP server.

## 5. Arsitektur

```
routers/services/scoring   (tidak berubah)
        |
repositories               (seam utama — hampir tak berubah)
  stock_price_repository   -> IdxEdgeProvider (price/history/verify)
  market_intelligence/repo -> IdxEdgeProvider (broker summary) + provider lama (celah)
  data/ticker_sync         -> IdxEdgeProvider (market-cap)
        |
providers
  idx_edge_provider  [BARU]  satu-satunya klien IDX Edge PRO
  ...provider lama...        hanya melayani celah
```

### 5.1 Modul baru `app/providers/idx_edge_provider.py`

Kelas `IdxEdgeProvider` — satu-satunya tempat yang menghubungi IDX Edge PRO.
Semua method **tidak pernah raise**: kembalikan `None`/`{}`/`[]` saat gagal
(konsisten dengan provider lama).

```python
class IdxEdgeProvider:
    async def fetch_history(code, frame="daily", limit=160) -> list[dict] | None
    async def fetch_price(code) -> dict | None
    async def search(q) -> list[dict]
    async def fetch_market_cap(page=1, per_page=50, codes=None) -> dict | None
    async def fetch_screener() -> dict | None
    async def fetch_broker_summary(code, start_date=None, end_date=None,
                                   flow="all", net=False, ...) -> dict | None
    async def health() -> dict | None
```

Fitur tambahan (akumulasi, seasonal, insider, financials, done-details) boleh
disiapkan di provider bila murah, tetapi belum disambungkan ke service/UI.

Implementasi:
- `httpx.AsyncClient` bersama, header `X-API-Key`, timeout dari settings.
- Panggil `await request_scheduler.acquire()` sebelum tiap request.
- Retry + backoff + jitter (reuse pola `_retry`), tangani 401/429/5xx.
- Normalisasi error HTTP → `None` + log, kecuali 401 (log konfigurasi tegas).

### 5.2 Config

Tambah di `app/config.py` dan `.env.example`:

```
IDX_EDGE_API_KEY=
IDX_EDGE_BASE_URL=https://stock.arjum.com
IDX_EDGE_TIMEOUT=20
IDX_EDGE_DAILY_QUOTA=1000
```

`.env` lokal diisi key nyata (tidak di-commit). Konfigurasi ini opsional-dimatikan:
bila `IDX_EDGE_API_KEY` kosong, perilaku kembali seperti semula (provider lama).

## 6. Pemetaan Data

### 6.1 Harga / History (kritis)

`StockPriceRepository.get_price/get_history` memakai `IdxEdgeProvider.fetch_history`
sebagai **primary** (provider lama untuk harga **dihapus**).

- `limit` dihitung dari period lewat `_period_to_limit` yang sudah ada.
- Adapter membentuk `pd.DataFrame` dengan index `DatetimeIndex` dari `date` dan
  kolom `Open, High, Low, Close, Volume` (kapitalisasi seperti `_flatten_columns`),
  diurutkan naik.
- Return `(df, is_simulated)`; `is_simulated=False` untuk data IDX Edge PRO.
- Bila `df` kosong/`None` → return `(None, False)`.
- Kelas lama `StockPriceProvider` **tidak dihapus** di Tahap 1, hanya dilepas dari
  jalur harga/verify (agar diff kecil & test lama tidak langsung pecah);
  penghapusan fisik menyusul di fase pembersihan.

### 6.2 Verifikasi Ticker

`StockPriceRepository.verify_ticker` → `IdxEdgeProvider.search(code)`, cocokkan
`stock_code == code` persis. Fallback (urutan): tabel `listed_tickers`, lalu
`VALID_TICKERS` statis. yfinance verify dihapus.

### 6.3 Sync Daftar Ticker

`app/data/ticker_sync.py`: sumber diganti ke `/api/market-cap` halaman demi
halaman (`per_page=50`). Upsert `ticker` + `company_name`; `sector` tetap NULL
(tidak tersedia). Sanity check jumlah tetap dipertahankan (tolak bila anjlok >10%).
Sumber Sectors.app dan scraping IDX pada sync **dihapus**. `SyncStatus` tetap.

### 6.4 Broker Summary (Market Intelligence)

`MarketIntelligenceRepository.get_broker_summary(limit)` diubah menjadi per-ticker
(`get_broker_summary(ticker, limit)`) memakai `/api/broker-summary/{code}`, lalu
dinormalisasi ke `BrokerItem` (`broker_code, broker_name, volume, value, frequency`).
`MarketIntelligenceService` meneruskan ticker. Endpoint MI belum dipakai frontend,
jadi perubahan signature aman.

Foreign flow, dividend, corporate action, earnings, analyst, price target tetap
memakai provider lama (celah).

## 7. Alur Screening (kuota)

`app/scheduler.run_batch_scan(mode)`:

1. `GET /api/screener/latest` (1 request) → daftar `stock_code` kandidat.
2. Untuk tiap kandidat: `stock_service.get_price` (history, ter-cache) → `calculate_score`.
3. Skor untuk `BSJP` dan `BPJS` dihitung dari **DataFrame yang sama** per kandidat
   (fetched sekali), jadi biaya ≈ jumlah kandidat, bukan 2× universe.
4. Persist ke `ScreeningResult` + cache `screen` seperti sekarang.
5. Jika `/api/screener/latest` gagal → pakai hasil cache terakhir; **jangan**
   fallback scan seluruh emiten (boros kuota). Log peringatan.

Perkiraan kuota harian: sync ticker ~20 + screener 1 + kandidat (mis. ≤50) +
riset/chat ad-hoc ≪ 1000.

## 8. Kuota & Error Handling

- Counter request harian di provider; reset pada pergantian hari WIB.
- Mendekati batas kuota → utamakan cache; request non-esensial dilewati + log.
- 401 → log "IDX_EDGE_API_KEY tidak valid/absen" (sekali), provider nonaktif.
- 429 → backoff; bila tetap gagal, kembalikan `None`.
- Tidak ada `raise` ke layer atas dari jalur IDX Edge PRO.

## 9. Data Palsu (mock)

- Jalur IDX Edge PRO: **tidak** memakai mock. Gagal → `(None, False)` / error,
  supaya UI menampilkan status sebenarnya.
- Mock lama tetap tersedia untuk provider celah dan tidak diubah.

## 10. Testing

- **Unit (tanpa jaringan)**: fixture JSON hasil respons nyata (disimpan di
  `tests/fixtures/`) untuk menguji adapter (`fetch_history` → DataFrame kolom &
  index benar; `search`; `market_cap` paginasi; `broker_summary` → `BrokerItem`).
- **Repository**: fallback verify (search → DB → statis); get_history error → `(None, False)`.
- **Update** `test_providers_smoke.py` (assertion wiring `IdxProvider` untuk harga diganti).
- **Regresi**: jalankan seluruh `test_*.py` yang ada.
- **Manual**: server menyala → `GET /api/stock/BBCA/history`, `POST /api/research`,
  `GET /api/screen`, `GET /api/market-intelligence/BBCA`.

## 11. Risiko

- **Kuota 1000/hari** ketat → dimitigasi pre-filter screener + cache + counter.
- **Kehilangan data celah** bila provider lama dimatikan → sengaja dipertahankan.
- **Perubahan kontrak MI** (broker per-ticker) → endpoint belum dipakai frontend.
- **Test lama** yang mengasumsikan yfinance/IdxProvider harga perlu diperbarui.

## 12. Out of Scope (fase berikutnya)

analysis, screener vendor sebagai fitur, akumulasi broker, seasonality, insider,
order flow, market cap (endpoint baru + UI), MCP server.
