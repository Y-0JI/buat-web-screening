# Desain: Deteksi Akumulasi Pemain Besar (Whale/Institusi)

Tanggal: 2026-10-01
Status: Menunggu implementasi (Tahap 0 belum diverifikasi)
Pendekatan: Funnel bertingkat hemat kuota, hasil disimpan harian, dilayani dari DB

## 1. Latar Belakang

Pengguna ingin menemukan saham IDX yang **BARU MULAI diakumulasi pemain besar**
(harga belum lari), lewat chat AI, hasil dirender sebagai kartu (mengikuti pola
kartu broker summary/fundamentals/chart yang sudah ada).

Kendala utama: kuota IDX Edge PRO **1000 request/hari**, universe ±963 emiten.
Scan penuh (history + broker per saham) tidak mungkin. Semua desain wajib hemat
kuota.

Catatan kejujuran domain: data IDX Edge tidak melabeli "institusi". Penanda yang
tersedia adalah broker besar (bandarmologi) dan arus asing (`flow=F`). Karena itu
`flow=F` **tidak boleh dilabeli "institusi"** di UI maupun reasons — sebut sebagai
"arus asing" saja.

## 2. Tujuan & Non-Tujuan

Tujuan:
- Tool baru untuk AI agent: `get_accumulation_candidates` (membaca hasil tersimpan).
- Screening harian otomatis (setelah pasar tutup) + trigger manual.
- Skor 0–100 dengan rincian komponen, alasan, kedalaman data, dan tanggal data.
- Kartu frontend baru; kasus kosong/error jelas.
- Backtest sederhana tanpa look-ahead, memakai data history yang ada.

Non-tujuan:
- Tidak menyentuh fitur lain.
- Tidak menambah dependency baru tanpa alasan kuat.
- Tidak membuat provider baru (pakai `IdxEdgeProvider` yang ada).
- Tidak memakai data palsu/mock di jalur produksi.
- Tidak mengklaim deteksi institusi dari data asing.

## 3. Batasan Kuota (wajib)

- **Sumber kebenaran kuota: header `x-ratelimit-remaining`** dari IDX Edge.
  Penghitung lokal (`_calls_today`) hanya cadangan bila header tidak ada.
- Funnel bertingkat; mahal hanya untuk kandidat yang lolos tahap murah.
- Mendekati batas: hentikan scan dengan rapi, simpan hasil **partial** dengan
  penanda "tidak lengkap". **Jangan** fallback ke scan seluruh emiten.
- Sisa kuota untuk chat ad-hoc pengguna harus tetap aman (sisakan cadangan,
  mis. `accumulation_quota_reserve`).

## 4. Config (satu tempat)

`backend/app/config.py`:

- `accumulation_enabled: bool = True`
- `accumulation_scan_token: str = ""` — secret untuk `POST /scan` (wajib non-kosong
  agar endpoint aktif; kosong = endpoint nonaktif).
- `accumulation_lookback_days: int = 20`
- `accumulation_history_limit: int = 150` — batas kandidat Tahap B
- `accumulation_broker_limit: int = 40` — batas kandidat Tahap C
- `accumulation_market_cap_min: float = 1e11` — batas bawah market cap (Tahap A)
- `accumulation_min_daily_value: float = 5e9` — likuiditas **absolut** (kolom
  `value` history) Tahap B; buang yang tipis
- `accumulation_max_history_limit: int = 250` — batas atas limit history (validasi
  sebelum request; API max 500)
- `accumulation_rotation_strata: int = 3` — jumlah strata market cap untuk rotasi
- `accumulation_max_runpct: float = 0.15` — buang yang sudah lari (N hari)
- `accumulation_quota_reserve: int = 50` — sisa kuota yang selalu disisakan
- `accumulation_foreign_broker_codes: str = ""` — daftar kode broker asing (opsional)
- `accumulation_weights: dict` — bobot tiap komponen skor

## 5. Skema Database

Tabel baru + migrasi Alembic idempoten (pola yang ada). Model di `database/models.py`.

### `accumulation_scans`
| Kolom | Tipe | Catatan |
|---|---|---|
| id | Integer PK | |
| scan_date | Date | tanggal data bursa (unik untuk idempotensi) |
| status | String(16) | `complete` / `partial` |
| universe_count | Integer | jumlah emiten setelah Tahap A |
| stage_b_count | Integer | jumlah kandidat Tahap B |
| stage_c_count | Integer | jumlah kandidat Tahap C |
| requests_used | Integer | jumlah request nyata siklus ini |
| quota_remaining | Integer | header terakhir bila ada |
| note | Text | alasan partial / catatan |
| created_at | DateTime | |

### `accumulation_signals`
| Kolom | Tipe | Catatan |
|---|---|---|
| id | Integer PK | |
| scan_id | FK accumulation_scans | |
| ticker | String(16) | |
| score | Float | 0–100 |
| depth | String(16) | `hv` / `foreign` / `broker` |
| components | JSON | **komponen mentah** (untuk re-skor) |
| reasons | Text | alasan bahasa manusia |
| close | Float | harga saat sinyal |
| foreign_net | Float | net asing (bila ada) |
| broker_net | Float | net broker besar (bila ada) |
| created_at | DateTime | |

Idempotensi: scan per `scan_date`; jika sudah ada scan `complete` untuk tanggal
itu, `POST /scan` tidak mengulang (kembalikan yang ada). Jika partial, boleh
dilanjutkan/ditimpa sesuai keputusan implementasi, tetap terikat 1 scan/tanggal.

## 6. Sinyal

### Harga-volume (Tahap B, dari history — tanpa request tambahan)
1. Divergensi OBV / Accumulation-Distribution terhadap harga.
2. Chaikin Money Flow.
3. Absorption: volume melonjak, range harga sempit.
4. Basing: sideways rapat setelah downtrend, atau higher low.
5. Posisi harga terhadap VWAP periodik.
6. Filter "belum lari": saham naik > `accumulation_max_runpct` dalam N hari dibuang.

### Arus asing (Tahap B, dari history)
7. Net foreign (`f_buy - f_sell`) positif & konsisten saat harga sideways.
   → depth `foreign`. **Jangan** sebut "institusi".

### Broker (Tahap C)
8. Konsentrasi net buy beberapa broker teratas selama N hari.
9. Average price pembeli vs harga sekarang (dekat = masih awal).
10. Persistensi net buy multi-hari (bukan satu hari).
    → depth `broker`.

Kedalaman data: `hv` (hanya harga-volume) < `foreign` (+ asing) < `broker` (+ broker).
Saham yang tidak sampai Tahap C **tidak** boleh dilabeli seperti terdeteksi whale;
`depth` dan `reasons` harus menyatakan itu.

## 7. Skor Akumulasi

- Skor 0–100 = jumlah berbobot komponen yang **tersedia**; bobot dinormalisasi
  hanya atas komponen yang ada (bobot di `accumulation_weights`).
- **Aturan plafon:** bila `depth != "broker"` (belum ada konfirmasi broker besar),
  skor dibatasi `accumulation_score_cap_no_broker` (default **60**); `depth="broker"`
  boleh sampai 100. Ditandai `capped=true` + alasan "skor dibatasi ...".
- **Tidak dinilai** (`rated=false`, `score=null`) untuk data kotor/kurang, suspensi,
  range nol, atau sudah lari — dengan alasan, bukan skor.
- Hasil per saham: ticker, skor, `depth` (hv/foreign/broker), rincian komponen
  **mentah** (`raw_signals`) + komponen ternormalisasi, alasan, `scan_date`.
- Komponen mentah disimpan agar bisa **re-skor** tanpa memanggil API ulang.
- Alasan tidak memakai kata "institusi": sebut "arus asing" / "broker besar".

## 8. Orkestrator Funnel

Kriteria Tahap A→B (ditetapkan dari hasil Tahap 0; market-cap **tidak memuat
pergerakan harga**):

1. **Seed screener** — ambil semua baris `screener/latest` (murah, 1 req). Bucket
   vendor (mis. "AKUMULASI SENYAP") **hanya penanda kandidat**, BUKAN komponen
   skor sampai backtest membuktikannya.
2. **Universe likuid + rotasi** — dari market-cap:
   - `turnover_ratio` bersifat **relatif** terhadap market cap (bukan likuiditas
     absolut). **Jangan** urutkan desc mentah-mentah.
   - Terapkan batas bawah `market_cap` (`accumulation_market_cap_min`).
   - **Hindari bias saham ramai**: stratifikasi universe per kelompok market cap
     (`accumulation_rotation_strata`) dan **rotasi irisan antar-hari**, supaya
     seluruh emiten terjangkau dalam N hari meski pasar sepi. Simpan kapan tiap
     ticker terakhir dicek (memungkinkan rotasi & re-scan).
3. Gabung + dedup + cap ke `accumulation_history_limit`.

- **Tahap B (sedang):** history harian untuk kandidat (≤ `history_limit`).
  Validasi limit ≤ `accumulation_max_history_limit` **sebelum** request. Ukur
  **likuiditas absolut** dari kolom `value` (buang yang tipis), hitung sinyal
  harga-volume + arus asing. Cek tanggal bar terbaru → **tandai data basi**.
  Filter "belum lari" dilakukan di sini.
- **Tahap C (mahal):** broker-accumulation/broker-summary hanya untuk kandidat
  teratas (≤ `broker_limit`). Finalisasi skor.
- Total request per hari dihitung & dicatat; sisa kuota aman (`quota_reserve`).
- **Validasi parameter sebelum request** (limit, rentang tanggal) — request gagal
  tetap memakan kuota.
- **Idempotent per tanggal data**; **skip akhir pekan/libur bursa** (berdasarkan
  tanggal data terakhir dari history/screener, bukan hari kalender).
- **Single-flight lock**: hanya satu scan berjalan; panggilan kedua ditolak/ditunggu.

## 9. Integrasi

- Repository `app/repositories/accumulation_repository.py` (akses DB, dict polos).
- Router `app/routers/accumulation.py`:
  - `POST /api/accumulation/scan` — **dilindungi secret token** (header
    `X-Scan-Token` == `accumulation_scan_token`) + **single-flight lock**.
  - `GET /api/accumulation/latest?limit=`
  - `GET /api/accumulation/{ticker}`
- Tool agent `get_accumulation_candidates(limit?)` **hanya membaca** hasil
  tersimpan. Deskripsi menjelaskan keterbatasan sinyal (bukan institusi).
- Event SSE baru `accumulation`; frontend render kartu.
- Frontend: tipe `ChatEvent` + `UIMessage.accumulations`, komponen
  `components/chat/accumulation.tsx`, render di `message.tsx`, state di
  `chat-app.tsx` (termasuk replay dari histori thread).

## 10. Penjadwalan

- Endpoint trigger + contoh unit **cron/systemd** (script di `backend/scripts/`),
  dijalankan setelah pasar tutup. Token dikirim lewat header.

## 11. Tahap 0 — Verifikasi Respons Nyata (checkpoint)

Sebelum implementasi lanjutan, dengan API key nyata panggil & tempel respons asli
(dipotong) + catat `x-ratelimit-remaining` sebelum/sesudah:

1. `history` harian: baris maksimal, apakah `f_buy`, `f_sell`, `n_foreign`, `avg` terisi.
2. `broker-accumulation`: bentuk `series`, `top_buyers`, `top_sellers`, rentang tanggal.
3. `broker-summary` rentang beberapa hari.
4. `screener/latest`: arti tiap `bucket`/field.
5. `market-cap`: apakah ada turnover/likuiditas untuk pre-filter murah.

Wajib juga: **menetapkan & melaporkan kriteria Tahap A→B** (karena market-cap
tidak memuat pergerakan harga). Komponen yang tidak tersedia → dilaporkan & dilewati,
tidak mengarang data.

## 12. Backtest

- Skrip `backend/scripts/backtest_accumulation.py`.
- Sinyal berskor tinggi pada tanggal historis → return 5/10/20 hari ke depan vs
  rata-rata sampel pasar.
- **Tanpa look-ahead**: hanya pakai data ≤ tanggal sinyal untuk skor; return masa
  depan hanya untuk evaluasi.
- Cache history agar tidak membebani kuota; laporkan apa adanya (termasuk tanpa edge).

## 13. Risiko

- "Institusi" hanya didekati via broker besar/arus asing; tidak ada label institusi.
- Belum ada data IHSG untuk pembanding pasar di backtest → pakai rata-rata sampel.
- Backtest historis butuh data scan nyata beberapa hari; alternatif re-skor jendela
  historis dibatasi kuota dan dinyatakan apa adanya.
- Akurasi sinyal tidak dijamin; tool ini alat riset, bukan saran keuangan.
