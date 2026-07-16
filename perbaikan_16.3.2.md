# Perbaikan 16.3.2 — Perbaiki Regresi dari Perbaikan 16.3.1

## Latar Belakang
Perbaikan 16.3.1 berhasil menyelesaikan sebagian besar masalah (riwayat chat, XSS, huruf kecil di pencarian, pembersihan dependency). Tapi perubahan pada cara riwayat chat dikirim ke AI dan perubahan pada penyimpanan cache screening per-mode ternyata memunculkan tiga masalah baru yang cukup penting. Dua di antaranya membuat fitur yang sudah diperbaiki sebelumnya jadi tidak berjalan dengan benar lagi.

## Tujuan
Membenahi tiga regresi baru ini tanpa mengulang lagi masalah yang sudah pernah diperbaiki di putaran sebelumnya (riwayat chat, XSS, huruf kecil, dsb — itu semua sudah benar, jangan diubah lagi).

## Ruang Lingkup

### 1. AI Chat tidak bisa lagi mengambil data saham/berita/fundamental (prioritas tertinggi, mendesak)
Setelah perbaikan cara riwayat chat dikirim ke AI, bagian yang menjalankan percakapan AI sekarang dieksekusi langsung di alur utama server, bukan lagi di jalur terpisah seperti sebelumnya. Masalahnya, fungsi-fungsi yang dipanggil AI untuk mengambil data saham, berita, dan data fundamental masih ditulis dengan asumsi mereka dijalankan di luar alur utama tersebut. Kombinasi ini membuat setiap kali AI mencoba memanggil salah satu dari fungsi-fungsi itu, hasilnya selalu error — jadi meskipun percakapan chat-nya sendiri tidak crash, AI jadi tidak pernah bisa lagi memberi jawaban yang berisi data saham yang sesungguhnya.

**Yang perlu dilakukan:** samakan cara eksekusi antara bagian yang menjalankan percakapan AI dan fungsi-fungsi pengambil data yang dipanggilnya, supaya keduanya konsisten — sama-sama berjalan di alur utama secara asynchronous (pakai `await` sampai ke bawah), atau sama-sama dijalankan di jalur terpisah seperti semula. Jangan campur dua gaya eksekusi yang berbeda dalam satu rangkaian pemanggilan.

### 2. Screening mode BPJS masih belum bisa memakai hasil pindaian penuh
Perbaikan sebelumnya sudah benar menjadwalkan pemindaian otomatis untuk kedua mode (BSJP dan BPJS). Tapi bagian yang membaca hasil pindaian dari penyimpanan sementara belum disesuaikan untuk membedakan mode mana yang sedang diminta pengguna — jadi walaupun data BPJS sudah ada di penyimpanan, permintaan screening BPJS tetap sering tidak mendapatkannya dan jatuh ke daftar cadangan yang terbatas.

**Yang perlu dilakukan:** pastikan bagian yang membaca hasil pindaian dari penyimpanan sementara benar-benar mengambil data sesuai mode yang diminta pengguna, bukan mengambil mode manapun yang kebetulan tersedia duluan.

### 3. Waktu "terakhir diperbarui" di hasil screening selalu kosong
Ada bagian kecil yang menampilkan kapan hasil screening terakhir dihasilkan. Setelah penyesuaian penyimpanan cache per-mode, bagian ini sekarang selalu mengembalikan kosong setiap kali dipanggil dari alur permintaan normal aplikasi, padahal sebelumnya berfungsi.

**Yang perlu dilakukan:** perbaiki supaya bagian ini bisa dipanggil dengan aman dari dalam alur permintaan asynchronous aplikasi (pakai cara yang konsisten dengan bagian lain yang mengakses penyimpanan cache yang sama), sehingga waktu terakhir diperbarui kembali muncul dengan benar di hasil screening.

### 4. Sisa kecil (boleh sekaligus, dampak rendah)
- Perhitungan MACD kemarin belum ikut dibenahi bareng EMA — samakan metode rata-rata bergeraknya juga supaya konsisten dengan EMA yang sudah dibenahi.
- Dependency `passlib` masih tercantum di `requirements.txt` tapi tidak dipakai di kode manapun — boleh dibuang. Kalau `bcrypt` memang dipakai langsung di kode, cantumkan sebagai dependency langsung, bukan cuma ikut kebawa dependency lain.

## Kriteria Penerimaan
- AI Chat bisa memberi jawaban yang berisi data saham/berita/fundamental yang sesungguhnya (bukan pesan error) saat ditanya soal saham tertentu.
- Screening mode BPJS mendapat hasil dari pemindaian penuh (bukan cuma daftar cadangan terbatas) ketika data pindaian untuk mode itu sudah tersedia.
- Waktu "terakhir diperbarui" muncul dengan benar di hasil screening, untuk kedua mode.
- Semua yang sudah benar dari Perbaikan 16.3.1 tetap benar (riwayat chat tidak dikirim ulang berlebihan, balasan AI tetap aman dari HTML/script, pencarian huruf kecil tetap terdeteksi).

## Verifikasi Wajib (harus dilakukan sebelum melaporkan pekerjaan selesai)
1. Jalankan aplikasi dengan API key AI yang valid, buka fitur chat, dan tanyakan sesuatu yang jelas-jelas butuh data saham (misal "gimana kondisi BBCA sekarang?"). Pastikan balasannya benar-benar berisi data (harga, skor, dst), bukan pesan error atau AI bilang gagal ambil data. Cek juga log server, pastikan tidak ada error terkait pemanggilan fungsi data di baliknya.
2. Uji dua kali: satu kali tanya soal satu saham, satu kali minta bandingkan atau minta berita — pastikan semua jenis pertanyaan yang butuh data tetap dapat jawaban valid.
3. Panggil fitur screening untuk mode BPJS dan mode BSJP secara terpisah setelah pemindaian otomatis berjalan (atau jalankan pemindaian manual untuk keduanya), lalu bandingkan jumlah saham yang muncul di masing-masing hasil — pastikan BPJS juga menunjukkan hasil dari cakupan penuh, bukan cuma segelintir saham.
4. Cek hasil screening kedua mode menampilkan waktu "terakhir diperbarui" yang valid, bukan kosong.
5. Ulangi pengujian regresi dari putaran sebelumnya: kirim beberapa pesan berurutan di chat dan pastikan tidak ada pemanggilan AI berlebih; coba masukkan karakter mirip HTML ke chat dan pastikan tetap aman; ketik nama saham huruf kecil di pencarian dan pastikan tetap terdeteksi.
6. Laporkan hasil tiap poin verifikasi di atas (berhasil/gagal + detail singkat), termasuk cuplikan log kalau ada error, sebagai bagian dari laporan penyelesaian.

## Catatan
Fokus utama putaran ini ada di poin 1 — itu yang bikin fitur AI Chat kehilangan fungsi utamanya. Setelah perbaikan, coba-coba dulu secara manual sebelum melaporkan selesai, jangan cuma mengandalkan kode terlihat benar tanpa dites langsung, karena masalah ini jenis yang tidak kelihatan dari sekadar membaca kode sekilas.
