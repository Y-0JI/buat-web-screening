# Perbaikan 16.3.3 — Benahi Tuntas Fitur AI Chat (Putaran Ketiga)

## Latar Belakang
Perbaikan 16.3.2 berhasil membenahi masalah screening BPJS dan waktu "terakhir diperbarui" dengan baik — itu sudah benar, jangan diubah lagi. Tapi perbaikan untuk fitur AI Chat malah membuat masalahnya lebih parah: sebelumnya AI Chat masih bisa membalas percakapan biasa (cuma gagal saat perlu ambil data saham), sekarang kemungkinan besar seluruh fitur chat tidak bisa membalas apa-apa sama sekali. Ini sudah tiga putaran perbaikan berturut-turut menyentuh bagian yang sama tanpa benar-benar tuntas, jadi kali ini perlu dibereskan sampai benar-benar teruji jalan, bukan cuma terlihat benar di kode.

## Tujuan
Membuat fitur AI Chat (termasuk kemampuannya memanggil data saham/berita/fundamental saat dibutuhkan) berjalan normal dan benar-benar teruji lewat pengujian manual nyata, bukan cuma dari membaca kode.

## Ruang Lingkup

### 1. Akar masalah: dua gaya eksekusi yang tidak konsisten
Bagian yang menjalankan percakapan dengan AI dan bagian yang dipanggilnya untuk mengambil data saham/berita/fundamental ditulis dengan dua gaya eksekusi berbeda (satu mengasumsikan dijalankan langsung di alur utama secara berurutan dengan `await`, satu lagi mengasumsikan dijalankan di jalur tersendiri di luar alur utama). Beberapa putaran perbaikan terakhir bolak-balik mengubah salah satu sisi saja tanpa menyamakan keduanya, sehingga kombinasinya selalu pincang di satu sisi atau sisi lain.

**Yang perlu dilakukan:** Pilih SATU pendekatan yang konsisten dari ujung ke ujung, lalu pastikan seluruh rantai pemanggilan (dari titik AI Chat menerima pesan pengguna, sampai ke fungsi-fungsi pengambil data saham/berita/fundamental yang dipanggil AI) mengikuti pendekatan yang sama itu. Jangan campur: kalau bagian pemroses percakapan ditulis dengan gaya yang butuh dijalankan berurutan dengan `await` sampai ke bawah, maka fungsi-fungsi pengambil data yang dipanggilnya juga harus ikut gaya itu (atau sebaliknya, kalau tetap mau dijalankan di jalur terpisah, maka bagian pemroses percakapan itu sendiri harus ditulis dengan gaya biasa/berurutan, bukan gaya yang butuh `await`).

Setelah selesai, baca ulang seluruh rantai pemanggilan dari awal sampai akhir dan pastikan tidak ada bagian yang "setengah diubah" — ini yang jadi penyebab regresi berulang di putaran-putaran sebelumnya.

### 2. Rapikan requirements.txt
Ada dependency yang tercantum dua kali di `backend/requirements.txt` akibat perbaikan sebelumnya. Cukup pastikan setiap dependency muncul satu kali saja.

## Kriteria Penerimaan
- Mengirim pesan biasa (tanpa perlu data saham) di fitur chat mendapat balasan normal dari AI.
- Mengirim pesan yang butuh data saham/berita/fundamental (misal tanya kondisi saham tertentu) mendapat balasan yang benar-benar berisi data itu, bukan pesan error dan bukan balasan kosong/gagal.
- Mengirim beberapa pesan berurutan dalam satu sesi chat tetap responsif dan tidak memicu pemanggilan AI berlebihan untuk pesan-pesan lama (jangan sampai perbaikan ini membuat masalah lama dari putaran-putaran sebelumnya muncul lagi).
- Tidak ada dependency yang tercantum dua kali di `requirements.txt`.

## Verifikasi Wajib (harus benar-benar dijalankan, bukan hanya membaca kode)
1. Jalankan aplikasi backend dengan API key AI yang valid dan benar-benar aktif.
2. Buka fitur chat, kirim pesan sapaan biasa (misal "halo"), pastikan dapat balasan teks yang wajar.
3. Kirim pesan yang jelas butuh data saham (misal "gimana kondisi BBCA sekarang?"), pastikan balasannya berisi data asli (ada angka harga/skor/dst), bukan pesan error dan bukan macet/timeout.
4. Kirim minimal 3-4 pesan lanjutan dalam sesi yang sama (percakapan yang saling nyambung), pastikan tiap balasan tetap normal dan responnya tidak melambat drastis dibanding pesan pertama.
5. Selama pengujian di atas, pantau log server secara langsung dan pastikan tidak ada exception/error yang muncul di balik layar, walaupun dari sisi pengguna balasannya terlihat muncul.
6. Sertakan cuplikan hasil pengujian (misal isi balasan AI yang didapat, atau potongan log yang menunjukkan tidak ada error) di laporan penyelesaian — bukan cuma pernyataan "sudah dites dan berhasil".
