# Perintah Perbaikan — buat-web-screening (BSJP AI)

> Catatan untuk agent: Ini daftar perbaikan untuk aplikasi BSJP AI. Kerjakan satu per satu sesuai urutan nomor. Setiap item sudah menyebutkan file yang harus diubah dan apa yang harus dicapai — kamu bebas menentukan cara implementasinya sendiri. Setelah selesai satu item, pastikan aplikasi masih bisa jalan normal sebelum lanjut ke item berikutnya.

---

## PRIORITAS 1 — Perbaiki dulu, ini paling penting

**1. Pendeteksi nama saham suka salah tangkap kata biasa**
File: `backend/app/routers/research.py` dan `frontend/src/app/page.tsx`.
Saat ini sistem mendeteksi kode saham dari pertanyaan user hanya dengan mencari kata pendek berhuruf kapital, tanpa mengecek apakah itu benar-benar kode saham yang ada di Bursa Efek Indonesia. Akibatnya kata biasa seperti "SAHAM" atau "KAPAN" bisa salah dikira kode saham. Perbaiki dengan mencocokkan hasil deteksi ke daftar kode saham yang valid, supaya kata biasa tidak ikut tertangkap.

**2. Nilai akhir saham bisa berubah sendiri dan bertentangan dengan analisisnya**
File: `backend/app/scoring/funnel.py`.
Ada aturan tambahan di akhir proses yang bisa memaksa hasil menjadi "BUY" hanya karena skor totalnya tinggi, walaupun analisis sebelumnya (funnel/confluence) sudah menyimpulkan "SELL". Ini bertentangan dengan prinsip yang sudah ditetapkan sejak awal, bahwa satu angka skor tidak boleh menimpa hasil analisis bertahap. Hapus aturan pemaksaan ini, supaya hasil akhir selalu konsisten dengan analisis funnel-nya.

**3. User yang sudah login bisa ter-lempar ke halaman login lagi**
File: `frontend/src/components/auth-guard.tsx` dan `frontend/src/lib/auth-context.tsx`.
Saat halaman dashboard di-refresh, sistem sempat mengira user belum login (karena datanya belum selesai dimuat), sehingga user yang sebenarnya sudah login ikut ter-lempar ke halaman login. Perbaiki supaya sistem menunggu proses pengecekan login selesai dulu, baru memutuskan perlu redirect atau tidak.

---

## PRIORITAS 2 — Fitur yang belum lengkap

**4. Tidak ada tombol untuk menyimpan saham ke watchlist**
File: `frontend/src/components/renderers/stock-report.tsx` (dan boleh juga `comparison.tsx`).
Fitur watchlist di backend sudah siap dipakai, tapi di halaman hasil riset saham belum ada tombol untuk menambahkannya ke watchlist. Tambahkan tombol "Tambah ke Watchlist" di kartu hasil riset, khusus untuk user yang sudah login.

**5. User tidak tahu kalau data yang ditampilkan itu bukan data asli**
File: `backend/app/data/fetcher.py`, dan bagian yang mengirim hasil ke frontend.
Kalau sumber data saham sedang bermasalah, sistem diam-diam memakai data simulasi/acak tanpa memberi tahu user. Tambahkan penanda di hasil analisis kalau datanya adalah data simulasi, lalu tampilkan peringatan kecil di tampilan hasil supaya user tahu.

---

## PRIORITAS 3 — Perbaikan kecil, boleh dikerjakan sekaligus

**6. Beberapa indikator (RSI, Volume, ATR, dll) kadang tampil kosong padahal seharusnya disembunyikan**
File: `frontend/src/components/renderers/stock-report.tsx` dan `comparison.tsx`.
Perbaiki pengecekan datanya supaya kalau nilainya memang tidak ada, kotak indikator itu tidak ikut ditampilkan sama sekali (bukan tampil kosong).

**7. Ada sisa kode di halaman ranking yang tidak berguna**
File: `frontend/src/components/renderers/ranking.tsx`.
Ada bagian kode yang terlihat seperti kondisi if/else, tapi dua pilihannya sama persis sehingga tidak ada gunanya. Sederhanakan jadi teks biasa saja.

**8. Preview gambar yang diupload bisa menumpuk di memori browser**
File: `frontend/src/components/upload-area.tsx`.
Setiap kali user upload gambar baru, gambar preview sebelumnya tidak dibersihkan dari memori. Tambahkan pembersihan otomatis saat ada upload baru.

**9. File contoh pengaturan (.env.example) belum lengkap**
File: `backend/.env.example`.
Ada beberapa pengaturan penting (termasuk kunci keamanan login) yang dipakai aplikasi tapi tidak dicontohkan di file ini. Lengkapi supaya siapa pun yang setup ulang project tidak bingung, dan beri catatan bahwa kunci keamanan wajib diganti sebelum dipakai online.

**10. Pengaturan akses (CORS) masih terbuka untuk semua domain**
File: `backend/app/main.py`.
Saat ini backend bisa diakses dari domain manapun tanpa batasan. Buat supaya daftar domain yang diizinkan bisa diatur lewat pengaturan environment, bukan selalu terbuka untuk semua.

---

## PRIORITAS 4 — Belum wajib, catatan untuk pengembangan lanjutan

**11. Ada fungsi indikator yang sudah ditulis tapi tidak pernah dipakai**
File: `backend/app/scoring/layers.py` dan `profiles.py`.
Ada satu fungsi indikator (opening range) yang sudah dibuat tapi belum benar-benar dipakai dalam perhitungan. Putuskan mau dihubungkan ke perhitungan skor mode BPJS, atau dihapus saja kalau tidak akan dipakai.

**12. Filter saham yang kena suspend/batas atas-bawah belum benar-benar dicek**
File: `backend/app/scoring/profiles.py` dan `funnel.py`.
Sistem seharusnya menyaring saham yang sedang suspend atau di batas ARA/ARB, tapi saat ini filternya hanya mengecek volume transaksi, bukan status saham yang sebenarnya. Perlu sumber data tambahan untuk mengecek status ini secara nyata.

**13. Belum ada analisis dari data akumulasi broker**
Ini fitur yang direncanakan tapi belum dibangun sama sekali — belum perlu dikerjakan sekarang, cukup jadi catatan untuk tahap berikutnya.

---

## Urutan kerja
Kerjakan nomor 1–3 dulu, lalu 4–5, lalu 6–10 bisa sekaligus, dan 11–13 terakhir kalau masih ada waktu.
