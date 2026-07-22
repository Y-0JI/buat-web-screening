# Perbaikan — Batch Scan IDX Kena Rate Limit (HTTP 429)

## Latar Belakang
Saat batch scan (BSJP + BPJS) jalan otomatis, log server penuh warning "HTTP Error 429" dari penyedia data IDX untuk hampir semua ticker. Ini membuat data profil perusahaan dan harga harian gagal diambil untuk sebagian besar saham, sehingga hasil screening jadi tidak lengkap.

Sistem sebenarnya sudah punya mekanisme pembatas laju permintaan (rate limiter) ke sumber data eksternal. Tapi ternyata masih ada satu bagian dari proses pengambilan data yang tidak ikut dibatasi oleh mekanisme itu — bagian ini mengirim permintaan tambahan ke server IDX di luar jalur yang sudah diatur, dan dijalankan berulang-ulang untuk setiap saham, bukan cuma sekali di awal. Ditambah lagi, dua mode scan (BSJP dan BPJS) berjalan bersamaan dan masing-masing memproses banyak saham secara paralel, jadi permintaan yang tidak dibatasi itu menumpuk jadi lonjakan besar dalam waktu singkat — inilah yang memicu server IDX menolak dengan HTTP 429.

## Tujuan
Batch scan bisa selesai tanpa dihujani error 429 dari IDX, dengan memastikan SEMUA jenis permintaan ke server IDX — termasuk permintaan "pemanasan sesi" di awal, bukan cuma permintaan pengambilan data utama — benar-benar melewati satu mekanisme pembatas laju yang sama, dan tidak diulang-ulang secara tidak perlu untuk tiap saham.

## Ruang Lingkup

### 1. Permintaan "pemanasan sesi" ke IDX tidak dibatasi & diulang tiap saham (prioritas tertinggi)
Ada proses persiapan koneksi/sesi ke server IDX yang dijalankan sebelum setiap pengambilan data (profil perusahaan, harga harian, dsb). Proses ini seharusnya cukup dilakukan satu kali saja selama aplikasi berjalan, tapi saat ini dijalankan ulang setiap kali ada permintaan data untuk satu saham. Proses ini juga tidak melewati mekanisme pembatas laju yang sudah ada, jadi saat banyak saham diproses bersamaan, proses persiapan sesi ini menghasilkan lonjakan permintaan tak terkendali ke server IDX.

**Yang perlu dilakukan:** ubah proses persiapan/pemanasan sesi ini supaya benar-benar hanya dijalankan sekali sepanjang umur aplikasi (bukan diulang tiap saham), dan pastikan aman dipanggil bersamaan dari banyak proses paralel tanpa menyebabkan sesi disiapkan berkali-kali secara bersamaan (race condition).

### 2. (Opsional — cek setelah perbaikan #1 selesai) Batas laju permintaan mungkin masih perlu disesuaikan
Setelah perbaikan #1 diterapkan, jalankan batch scan lagi dan amati log. Kalau error 429 masih muncul — meski jauh lebih jarang — khusus dari permintaan pengambilan data utama (bukan dari proses pemanasan sesi), berarti volume permintaan bersamaan dari dua mode scan yang jalan sekaligus masih terlalu tinggi untuk batas laju yang ada saat ini.

**Yang perlu dilakukan (hanya jika masih terjadi):** turunkan batas jumlah permintaan per menit ke server IDX ke angka yang lebih aman, dan/atau atur supaya kedua mode scan tidak sama-sama mengirim permintaan dalam volume besar di waktu yang persis bersamaan.

## Kriteria Penerimaan
- Batch scan harian (BSJP + BPJS) selesai berjalan tanpa banjir warning HTTP 429 di log.
- Jumlah saham yang berhasil terisi datanya (profil & harga) di hasil akhir scan meningkat signifikan dibanding sebelum perbaikan.
- Terbukti proses pemanasan/persiapan sesi ke IDX tidak lagi dijalankan berulang untuk tiap saham.

## Verifikasi Wajib (harus benar-benar dijalankan, bukan hanya membaca kode)
1. Jalankan batch scan penuh (BSJP + BPJS) dari server yang baru dinyalakan, lalu hitung berapa kali warning HTTP 429 muncul di log — bandingkan dengan kondisi sebelum perbaikan.
2. Buktikan proses pemanasan sesi cuma jalan sekali (misal lewat satu baris log khusus tiap kali proses itu benar-benar dieksekusi) — jalankan scan, baris log tersebut harus muncul 1 kali saja meskipun banyak saham diproses.
3. Cek hasil akhir scan (data yang tersimpan/tercache) — pastikan mayoritas saham sekarang punya data profil & harga terisi, bukan kosong/error karena 429.
4. Laporkan hasil tiap poin verifikasi di atas (berhasil/gagal + detail singkat, termasuk angka jumlah 429 sebelum vs sesudah) sebagai bagian dari laporan penyelesaian.
