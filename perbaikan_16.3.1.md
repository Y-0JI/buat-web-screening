# Perbaikan 16.3.1 — Stabilitas Chat AI, Keamanan Frontend, dan Konsistensi Screening

## Latar Belakang
Review menyeluruh terhadap hasil Perbaikan 16.1–16.3 menemukan beberapa masalah baru di alur AI Chat, keamanan tampilan chat, dan konsistensi fitur screening BSJP/BPJS. Masalah-masalah ini tidak menyebabkan aplikasi crash secara langsung, tapi berdampak ke biaya operasional, keamanan, dan pengalaman pengguna.

## Tujuan
Menghilangkan pemborosan pemanggilan AI yang tidak perlu, menutup celah keamanan di tampilan chat, dan memastikan fitur screening konsisten untuk kedua mode trading (BSJP & BPJS).

## Ruang Lingkup

### 1. Riwayat percakapan AI Chat dikirim ulang secara tidak efisien (prioritas tertinggi)
Saat ini, setiap kali pengguna mengirim pesan baru di fitur chat, sistem mengirim ulang seluruh pesan-pesan lama satu per satu ke AI seolah-olah itu pesan baru, sebelum akhirnya memproses pesan yang benar-benar baru. Ini membuat satu kali kirim pesan bisa memicu banyak kali pemanggilan AI yang hasilnya dibuang begitu saja — boros biaya, boros waktu tunggu, dan berisiko bikin percakapan jadi rusak/error kalau salah satu pesan lama itu sempat memicu pemanggilan tool.

**Yang perlu dilakukan:** ubah cara riwayat percakapan diberikan ke AI supaya cukup diberikan sekali sebagai konteks awal, bukan dikirim ulang satu per satu. Hanya pesan terbaru dari pengguna yang seharusnya benar-benar memicu satu kali pemrosesan oleh AI. Cek dokumentasi/SDK resmi Google Gen AI Python untuk cara yang benar membuat sesi chat dengan riwayat percakapan sebelumnya.

### 2. Balasan AI di panel chat berpotensi celah keamanan (XSS)
Teks balasan dari AI di panel chat saat ini dirender langsung sebagai HTML mentah setelah sebagian format markdown-nya diubah, tanpa mengamankan teks dari karakter HTML yang mungkin ikut terbawa. Kalau balasan AI (atau data yang dikutip AI dari berita/tool) mengandung karakter seperti `<` dan `>`, itu bisa dieksekusi sebagai kode HTML/script asli di browser pengguna, bukan sekadar ditampilkan sebagai teks.

**Yang perlu dilakukan:** pastikan teks balasan AI di-escape/diamankan dari karakter HTML terlebih dahulu, baru kemudian format markdown-nya (bold, italic, list, dst) diterapkan di atas teks yang sudah aman. Boleh pakai library markdown-to-React yang sudah teruji, atau lakukan escaping manual sebelum konversi markdown.

### 3. Pencarian ticker di kotak chat/pencarian tidak mengenali huruf kecil
Bagian yang mendeteksi kode saham dari ketikan pengguna di workspace (untuk fitur bandingkan & buka riset otomatis) hanya mengenali huruf besar. Kalau pengguna mengetik dengan gaya santai huruf kecil (mis. "bandingkan bbca vs bbri"), sistem gagal mengenali kode sahamnya sama sekali dan pengguna diarahkan ke alur yang salah tanpa pemberitahuan yang jelas.

**Yang perlu dilakukan:** pastikan teks dari pengguna diseragamkan ke huruf besar dulu sebelum dicocokkan dengan pola kode saham, di semua tempat client-side yang melakukan deteksi ticker dari input pengguna.

### 4. Screening mode BPJS tidak pernah memakai data pindaian penuh
Proses pemindaian otomatis seluruh saham IDX (yang berjalan terjadwal tiap sore) hanya pernah dijalankan untuk mode BSJP. Sementara itu, pengguna sekarang bisa memilih mode BPJS di halaman screening. Akibatnya, screening BPJS selalu jatuh ke daftar cadangan yang jumlahnya sangat terbatas, tidak pernah mendapat hasil dari pemindaian penuh seperti BSJP.

**Yang perlu dilakukan:** jadwalkan pemindaian otomatis untuk kedua mode (BSJP dan BPJS), atau kalau demi efisiensi cuma mau jalankan satu mode di jadwal otomatis, pastikan ada penjelasan yang jelas ke pengguna di tampilan kalau mode BPJS memakai data terbatas. Idealnya: kedua mode punya data pemindaian penuh yang setara.

### 5. Pemanggilan tool AI Chat berpotensi konflik data saat dipakai bersamaan (prioritas lebih rendah, boleh dikerjakan belakangan)
Fungsi-fungsi yang dipanggil AI saat chat (ambil data saham, berita, fundamental) berjalan di jalur eksekusi terpisah dari server utama, tapi tetap mengakses cache data yang sama dengan jalur utama. Kalau ada permintaan chat dan permintaan riset biasa berjalan bersamaan, ada risiko kecil data cache saling tabrakan.

**Yang perlu dilakukan:** sederhanakan supaya fungsi-fungsi tool AI Chat memakai jalur eksekusi async yang sama dengan bagian lain aplikasi (bukan menjalankan loop event terpisah di dalam thread), sehingga semuanya konsisten memakai satu mekanisme pengamanan data yang sama.

### 6. Rapikan sisa-sisa kecil (boleh sekaligus, dampak rendah)
- Perhitungan EMA dan MACD sebaiknya memakai metode perhitungan rata-rata bergerak yang sama dengan yang dipakai platform trading pada umumnya, supaya angkanya tidak menyimpang dari yang biasa dilihat trader di TradingView/MetaTrader.
- Bagian yang mengambil ringkasan sentimen pasar dari AI (fitur insight market) punya potensi masalah yang sama dengan parsing hasil analisis gambar: kalau AI menjawab lebih dari satu baris, sebagian isi bisa hilang. Pastikan cara membaca hasil jawaban AI tidak bergantung pada asumsi jawabannya selalu satu baris.
- Bersihkan dependency yang tercantum di `requirements.txt` tapi sudah tidak dipakai di kode sama sekali, dan pastikan dependency yang benar-benar dipakai langsung (bukan cuma kebawa tidak langsung lewat dependency lain) tercantum secara eksplisit.

## Kriteria Penerimaan
- Mengirim pesan chat baru pada percakapan yang sudah panjang tidak memicu pemanggilan AI berulang untuk pesan-pesan lama.
- Balasan AI di panel chat tidak bisa dipakai untuk menyisipkan HTML/script aktif ke halaman.
- Mengetik nama saham huruf kecil di pencarian/chat tetap terdeteksi dengan benar.
- Screening BPJS dan BSJP setara dari sisi cakupan data (atau pengguna diberi tahu dengan jelas kalau tidak).
- Tidak ada regresi terhadap perbaikan-perbaikan sebelumnya (mode BSJP/BPJS di research, compare, dan chat tetap berfungsi; autentikasi tetap berjalan; data teknikal & fundamental tetap tampil).

## Verifikasi Wajib (harus dilakukan sebelum melaporkan pekerjaan selesai)
1. Jalankan aplikasi backend & frontend secara lokal, lalu uji manual: buka fitur chat, kirim minimal 4-5 pesan berurutan dalam satu sesi, dan pastikan tidak ada pemanggilan AI berlebih (cek log/jumlah request) untuk pesan-pesan lama.
2. Coba masukkan teks yang mengandung karakter mirip HTML (misal tanda `<` `>`) ke input chat dan pastikan itu tampil sebagai teks biasa, bukan dieksekusi oleh browser.
3. Uji ketik query pencarian/chat dengan huruf kecil yang mengandung nama saham (mis. "bandingkan bbca vs bbri") dan pastikan sistem tetap mengenali kode sahamnya.
4. Cek endpoint/fitur screening untuk kedua mode (BSJP & BPJS) dan bandingkan jumlah saham yang muncul di hasilnya.
5. Ulangi pengujian regresi dasar dari perbaikan-perbaikan sebelumnya: login/register, riset satu saham di kedua mode, bandingkan saham, dan pastikan tidak ada error baru di log server.
6. Laporkan hasil tiap poin verifikasi di atas (berhasil/gagal + detail singkat) sebagai bagian dari laporan penyelesaian, bukan cuma menyatakan "sudah selesai".

## Catatan
Dokumen ini sengaja ditulis pada level konsep, bukan level baris kode. Coding agent bebas menentukan cara implementasi paling sesuai dengan struktur kode yang ada, selama tujuan dan kriteria penerimaan di atas terpenuhi.
