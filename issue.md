# BSJP dan BPJS AI — Blueprint Produk
### Full AI Search Platform untuk Analisis Saham Indonesia

> **Catatan untuk agent:** Dokumen ini adalah spesifikasi produk level tinggi (high-level). Tujuannya menjadi acuan konsep dan arsitektur untuk membangun ("vibe coding") aplikasi ini — bukan spesifikasi teknis baris-per-baris. Detail implementasi (nama variabel, struktur folder, versi library, dsb.) diserahkan pada kebijakan agent/tim yang membangun. Ikuti prinsip dan urutan di dokumen ini, bukan kata-katanya secara harfiah.

---

## 1. Ringkasan & Visi Produk

BSJP AI adalah aplikasi riset saham Indonesia yang seluruh interaksinya dimulai dari satu search bar, mengikuti pola "AI search" (mirip Claude Quick Search) — bukan dashboard tradisional dengan banyak menu/filter, dan bukan pula chatbot teks biasa.

User cukup mengetik pertanyaan dalam bahasa natural. Sistem melakukan riset, menghitung indikator, memberi skor, lalu menyajikan hasil dalam tampilan visual terstruktur secara otomatis.

## 2. Target Pengguna & Masalah yang Diselesaikan

- **Target:** Trader/investor ritel Bursa Efek Indonesia (BEI) yang butuh riset cepat sebelum mengambil keputusan, khususnya untuk swing/day-trading ("BSJP" — beli sore jual pagi).
- **Masalah:** Tools riset yang ada saat ini menuntut pengguna memahami banyak indikator dan membuka banyak tab/aplikasi sekaligus.
- **Solusi:** Satu titik masuk (search bar) yang memahami maksud user, lalu AI yang menjalankan riset teknikal dan menyajikan kesimpulan siap pakai.

## 3. Cakupan Fitur Utama

- Riset mendalam satu saham (fundamental ringan + teknikal).
- Screening/ranking harian — saham paling layak dipantau untuk sesi berikutnya.
- Perbandingan dua saham atau lebih secara berdampingan.
- Analisis visual dari lampiran user (screenshot chart, order book).
- Percakapan lanjutan (follow-up question) atas hasil riset yang sudah ditampilkan.

## 4. Arsitektur Alur Sistem

Alur inti (high level), berlaku untuk mode on-demand (saat user bertanya) maupun mode terjadwal (batch scan otomatis di luar jam bursa untuk menyiapkan watchlist):

```
Query User → AI Agent (Orchestrator)
    → Lapisan Data (harga/volume + lampiran opsional user)
    → Mesin Indikator & Scoring
    → Model AI (reasoning + narasi)
    → Output Terstruktur (JSON)
    → Renderer UI Dinamis → Tampilan ke User
```

- **Mode on-demand:** dipicu langsung oleh pertanyaan user, real-time.
- **Mode terjadwal:** berjalan otomatis pasca penutupan bursa, hasilnya di-cache agar siap ditampilkan tanpa menunggu saat dibuka keesokan harinya.

## 5. Lapisan Data & Indikator

- **Sumber data pasar:** Data harga, volume, dan riwayat pergerakan saham diambil lewat `yfinance` — pustaka Python open-source & gratis untuk mengakses data Yahoo Finance. Perlu diperhitungkan bahwa data semacam ini umumnya delayed, bukan real-time tick-by-tick.
- **Sumber data tambahan (opsional):** Screenshot chart atau order book yang diunggah user, dibaca lewat kemampuan vision model AI.
- **Indikator inti:** EMA, RSI, MACD, ATR, VWAP, volume relatif, gap, serta level support/resistance sebagai indikator dasar wajib.
- **Perluasan:** Arsitektur indikator sebaiknya modular, agar indikator/struktur analisis lanjutan (mis. analisis struktur harga ala smart money, akumulasi broker) dapat ditambahkan belakangan sebagai layer baru tanpa mengubah pipeline inti.

## 6. Metodologi Scoring

- **Skor & verdict:** Setiap saham diberi skor komposit 0–100, dipetakan ke kategori keputusan: `BUY` / `HOLD` / `SELL` / `AVOID`, disertai tingkat keyakinan (confidence/probability).
- **Prinsip funnel, bukan rata-rata:** Hindari model "rata-rata semua indikator jadi satu angka" — pendekatan ini rawan membiarkan satu sinyal kuat (mis. lonjakan volume) menutupi sinyal lain yang justru bertentangan (mis. struktur harga masih downtrend). Gunakan pola funnel: layer awal bertindak sebagai filter/veto (likuiditas, freefloat, status ARA/ARB), layer berikutnya baru menilai arah & kekuatan sinyal.
- **Verdict berbasis confluence:** Verdict BUY idealnya disyaratkan lolos beberapa kondisi sekaligus (mis. struktur/arah positif DAN volume terkonfirmasi DAN tidak kena veto regulasi) — bukan sekadar total skor melewati satu angka ambang. Ini mencegah satu faktor dominan mengalahkan sinyal yang saling bertentangan.
- **Confidence berbasis backtest:** Angka confidence/probability sebaiknya dikalibrasi dari data historis (mis. dari N kejadian pola serupa di masa lalu, berapa persen yang berlanjut sesuai arah) — bukan estimasi sesaat dari model AI, agar angka tersebut benar-benar mencerminkan statistik, bukan tebakan.
- **Output risk-adjusted:** Verdict sebaiknya turut menyertakan level stop-loss (mis. dari ATR) dan estimasi risiko, tidak berhenti di arah (BUY/SELL) saja.
- **Transparansi:** Setiap verdict harus disertai ringkasan alasan singkat (naratif) yang bisa dibaca cepat, bukan hanya angka.

BSJP (beli sore jual pagi) dan BPJS/intraday (beli pagi jual sore) menebak hal yang berbeda — funnel & bobot layer sebaiknya dibuat sebagai **dua profil terpisah**, bukan satu formula yang sama untuk keduanya:

| Layer / Prioritas | Mode BSJP (Sore → Pagi) | Mode BPJS / Intraday (Pagi → Sore) |
|---|---|---|
| **Filter wajib (veto)** | Likuiditas & freefloat cukup; buang saham suspend/ARB. | Likuiditas tinggi (harus bisa exit di hari sama); buang saham yang sudah dekat ARA di awal sesi. |
| **Sinyal utama** | Kekuatan closing — strong close dekat high vs reject dari atas. | Klasifikasi gap: continuation (didukung tren & volume) vs exhaustion (rawan fade). |
| **Konfirmasi** | Broker accumulation yang terkonsentrasi di sesi sore. | Opening range breakout 15–30 menit pertama + relative strength vs indeks. |
| **Volume** | Lonjakan volume sesi akhir — bedakan akumulasi vs distribusi terselubung. | Volume 30 menit pertama dibanding rata-rata di jam yang sama (bukan volume harian). |
| **Struktur & risiko** | RSI/MACD/ekstensi dari EMA sebagai filter risiko, bukan sinyal utama. | VWAP intraday sebagai acuan bias & filter ekstensi harga. |
| **Katalis** | Berita/aksi korporasi sore yang belum ter-price-in penuh. | Katalis dengan asal-usul jelas — lebih tahan dibanding gap tanpa alasan konkret. |
| **Risiko khas** | Closing di ARA butuh aturan sendiri (dua arah); volume besar belum tentu akumulasi. | Whipsaw jam pembukaan; biaya transaksi proporsional lebih besar; waspadai overlap dengan kandidat BSJP kemarin yang rawan profit-taking pagi ini. |

## 7. Prinsip Desain Interaksi (UX)

- Search bar sebagai satu-satunya titik masuk utama; hindari dashboard multi-menu di layar awal.
- Sediakan opsi lampiran (upload chart / order book) berdampingan dengan search bar, bukan di menu terpisah.
- Tampilkan beberapa contoh pertanyaan di halaman awal untuk membantu user memahami kemampuan sistem (onboarding tanpa tutorial panjang).
- Hasil riset selalu tersaji sebagai kartu/dashboard visual yang konsisten formatnya, bukan balasan teks panjang tak terstruktur.

## 8. Output Terstruktur & Rendering Dinamis

Ini adalah pola arsitektur inti dari BSJP AI dan wajib dipertahankan siapa pun yang mengimplementasikan sistem ini:

- Model AI tidak pernah menghasilkan HTML atau tampilan langsung.
- Model AI hanya mengeluarkan data terstruktur (JSON) yang salah satu fieldnya menentukan jenis tampilan ("tipe render").
- Frontend memiliki satu komponen tampilan untuk tiap tipe render, dan memilih komponen yang sesuai berdasarkan field tersebut.
- Menambah kemampuan baru = menambah satu tipe render + satu komponen baru, tanpa mengubah logika AI yang sudah ada.

Contoh gambaran singkat (bukan skema final):

```json
{
  "render": "stock-report",
  "ticker": "RGAS",
  "score": 92,
  "verdict": "BUY",
  "confidence": 89,
  "summary": "..."
}
```

**Tipe render minimal yang dibutuhkan:**
- `stock-report` → dashboard riset satu saham.
- `comparison` → tampilan perbandingan antar saham.
- `ranking` → daftar/urutan saham hasil screening.
- `vision-analysis` → hasil pembacaan chart/order book yang diunggah.

## 9. Contoh Skenario Penggunaan

- **Riset satu saham** — User: *"Research RGAS"* / *"Apakah RGAS layak untuk BSJP besok?"* → sistem mengembalikan satu kartu `stock-report` lengkap dengan skor, verdict, dan ringkasan alasan.
- **Screening harian** — User: *"Cari saham terbaik besok"* → sistem memindai seluruh saham, mengembalikan daftar `ranking` singkat (top 5–10) beserta skor masing-masing, dan menawarkan analisis lengkap saham teratas.
- **Perbandingan & analisis visual** — User: *"Bandingkan BBCA dan BRIS"* atau mengunggah screenshot chart/order book → sistem mengembalikan tampilan `comparison` atau `vision-analysis` yang menggabungkan hasil baca gambar dengan data pasar.

## 10. Rekomendasi Stack Teknologi

Prioritas dipilih ke tools gratis/open-source di setiap lapisan, agar proyek bisa dibangun dan dijalankan tanpa biaya lisensi. Layanan berbayar hanya disebut sebagai opsi cadangan bila dibutuhkan skala lebih besar.

- **Frontend:** Next.js, React, TailwindCSS, shadcn/ui — seluruhnya open-source & gratis.
- **Backend:** FastAPI (Python) — open-source & gratis.
- **AI (reasoning & vision):** Gemini API free tier (model Flash / Flash-Lite) — gratis tanpa kartu kredit, tidak butuh komputer kuat karena semua pemrosesan di server Google, dan sudah mendukung teks + vision sekaligus (cocok untuk baca chart/order book). Cukup untuk kebutuhan riset personal skala harian. Catatan: ada batas jumlah request per menit/hari (free tier saat ini sekitar 15 request/menit, ~1.500 request/hari), dan input pada free tier bisa dipakai Google untuk peningkatan model — hindari mengirim data yang sifatnya rahasia. Kalau limit ini kelak kurang, opsi lain: OpenRouter/Groq sebagai cadangan, atau upgrade ke tier berbayar Gemini yang tetap tergolong murah.
- **Data pasar:** `yfinance` — pustaka open-source & gratis untuk data harga/volume saham.
- **Database:** PostgreSQL self-hosted — open-source, gratis tanpa batas. Supabase bisa jadi opsi bila ingin kemudahan hosting terkelola (free tier tersedia, berbayar di skala besar).
- **Scheduler & cache:** APScheduler (Python) atau cron biasa untuk scan terjadwal, plus lapisan cache sederhana untuk hemat pemanggilan API eksternal — keduanya tidak butuh layanan berbayar.
- **Deployment & CI/CD:** Self-hosting via Docker di VPS sendiri untuk jangka panjang paling hemat, atau manfaatkan free tier platform hosting (mis. Vercel untuk frontend, Render/Fly.io untuk backend) selama tahap MVP. GitHub Actions untuk CI/CD dasar, gratis untuk skala proyek ini.

## 11. Scaffolding & Tooling Proyek

Bagian ini memberi kerangka awal proyek secara konseptual, agar coding agent punya arah sejak commit pertama — tanpa mengunci ke struktur folder atau perintah yang kaku.

- **Modul/boundary konseptual:** Frontend app (UI + renderer dinamis), Backend API (orchestrator query), AI orchestration layer (prompt & pemanggilan Gemini API), Data layer (koneksi data pasar + parser lampiran), Scoring engine (kalkulasi indikator & skor), Worker/scheduler (batch scan terjadwal). Sebaiknya dipisah sebagai modul/service independen agar mudah diuji dan dikembangkan terpisah.
- **Environment variables inti:** Kunci API Gemini, kredensial database, dan konfigurasi sumber data pasar. Disimpan di file environment terpisah, tidak pernah masuk version control.
- **Dev tooling dasar:** Linter & formatter otomatis, kerangka testing khusus untuk memvalidasi skema JSON output dan hasil mesin scoring, serta konvensi commit yang jelas sejak awal.
- **Strategi deployment:** Kontainerisasi (mis. Docker) untuk backend/worker agar konsisten antar environment; frontend dan backend di-deploy terpisah supaya bisa scaling independen; pipeline CI/CD minimal (build → test → deploy) sudah aktif sejak fase MVP.
- **Titik awal pengembangan:** Mulai dari backend — data layer, scoring engine, dan satu endpoint riset saham — sebelum menyentuh frontend, karena tampilan bergantung pada skema JSON yang dihasilkan backend.

## 12. Pertimbangan Non-Fungsional & Batasan

- **Disclaimer:** Setiap output verdict wajib menyertakan penegasan bahwa hasil AI adalah alat bantu riset, bukan rekomendasi investasi resmi.
- **Rate limit & biaya:** Panggilan ke API eksternal (data pasar, AI) perlu dibatasi/di-cache supaya tidak menyentuh limit atau membengkakkan biaya.
- **Keamanan:** Kunci API disimpan dan dipanggil hanya dari sisi backend, tidak pernah diekspos ke client.
- **Keandalan:** Skema JSON output perlu divalidasi sebelum dikirim ke frontend, untuk mencegah tampilan rusak akibat respons AI yang tidak terduga.

## 13. Roadmap Implementasi Bertahap

Dipecah menjadi fase agar bisa dibangun bertahap oleh coding agent, dari MVP ke fitur lanjutan:

| Fase | Tujuan | Cakupan |
|---|---|---|
| **Fase 1 (MVP)** | Validasi konsep inti | Search bar tunggal, riset satu saham, indikator dasar, output JSON, satu tipe render (`stock-report`). |
| **Fase 2** | Perluasan riset | Tambah tipe render `comparison` & `ranking`; aktifkan mode scan terjadwal (batch post-market). |
| **Fase 3** | Input visual | Upload & analisis chart/order book lewat vision model; tipe render `vision-analysis`. |
| **Fase 4** | Personalisasi & scoring lanjutan | Akun user, riwayat & watchlist pribadi, layer scoring tambahan (mis. struktur harga lanjutan, akumulasi broker). |

## 14. Kesimpulan

BSJP AI bukan dashboard konvensional maupun chatbot biasa. Intinya adalah satu search bar sebagai titik masuk, AI yang melakukan riset dan scoring di belakang layar, dan output terstruktur yang secara otomatis dirender menjadi tampilan profesional oleh frontend — sehingga sistem tetap konsisten dan mudah dikembangkan seiring bertambahnya fitur.
