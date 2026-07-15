# Perbaikan 16.1.2

## Tujuan

Lakukan perbaikan pada backend dan frontend untuk meningkatkan
stabilitas, konsistensi fitur, keamanan, serta mengurangi technical debt
tanpa mengubah perilaku utama aplikasi.

## Daftar Pekerjaan

### 1. Modernisasi dependency AI

-   Migrasikan penggunaan SDK Gemini yang sudah deprecated ke SDK
    terbaru.
-   Bersihkan dependency yang sudah tidak digunakan.
-   Pastikan seluruh dependency yang memang dipakai dideklarasikan
    secara eksplisit.

### 2. Pengamanan konfigurasi

-   Tambahkan validasi konfigurasi saat aplikasi dijalankan agar
    konfigurasi default yang tidak aman tidak dapat digunakan pada
    environment production.

### 3. Perbaikan proses registrasi

-   Tingkatkan proses pendaftaran akun agar aman terhadap request yang
    berjalan bersamaan.
-   Pastikan jika terjadi username atau email duplikat, aplikasi
    mengembalikan pesan yang sesuai, bukan internal server error.

### 4. Konsistensi mode analisis (BSJP/BPJS)

-   Pastikan mode analisis yang dipilih pengguna digunakan secara
    konsisten pada seluruh proses screening, comparison, batch scan, dan
    AI chat.
-   Jangan menggunakan mode default apabila pengguna sudah menentukan
    mode tertentu.

### 5. Perbaikan sistem cache data saham

-   Pisahkan mekanisme cache untuk proses validasi ticker dan proses
    pengambilan data utama agar tidak saling memengaruhi.
-   Hindari kondisi di mana hasil validasi sementara menyebabkan data
    riset menjadi tidak akurat.

### 6. Peningkatan keamanan concurrent access

-   Pastikan akses terhadap cache dan data bersama aman ketika dipanggil
    secara bersamaan dari beberapa request atau thread.

### 7. Penyempurnaan indikator teknikal

-   Perbaiki perhitungan RSI pada kondisi harga bergerak datar agar
    menghasilkan nilai yang benar.
-   Samakan implementasi EMA dan MACD dengan standar yang umum digunakan
    oleh platform charting.

### 8. Penyempurnaan scoring dan confidence

-   Sesuaikan logika confidence agar mempertimbangkan arah rekomendasi
    (BUY atau SELL), sehingga hasil penilaian lebih representatif.

### 9. Penyempurnaan perhitungan VWAP

-   Gunakan pendekatan VWAP yang sesuai dengan praktik umum, terutama
    jika digunakan sebagai dasar analisis intraday.

### 10. Peningkatan parsing AI Vision

-   Perbaiki proses pembacaan respons AI Vision agar mampu mengambil
    analisis yang terdiri dari beberapa baris, bukan hanya satu baris.

### 11. Sinkronisasi frontend

-   Pastikan seluruh request dari frontend mengirimkan mode analisis
    yang dipilih pengguna.
-   Jaga konsistensi implementasi dengan backend.

### 12. Evaluasi penyimpanan token autentikasi

-   Tinjau kembali mekanisme penyimpanan JWT.
-   Jika memungkinkan, gunakan pendekatan yang lebih aman dibanding
    penyimpanan langsung di local storage.

## Acceptance Criteria

-   SDK AI telah menggunakan versi terbaru.
-   Dependency yang tidak digunakan telah dihapus.
-   Konfigurasi production lebih aman.
-   Registrasi tidak menghasilkan error ketika terjadi request
    bersamaan.
-   Mode BSJP/BPJS bekerja konsisten di seluruh fitur.
-   Cache lebih akurat dan tidak saling mengganggu.
-   Aplikasi aman terhadap concurrent access.
-   Perhitungan indikator teknikal lebih akurat.
-   Confidence scoring lebih sesuai dengan hasil analisis.
-   VWAP mengikuti implementasi yang tepat.
-   AI Vision dapat membaca respons multi-baris.
-   Frontend dan backend menggunakan mode analisis yang sama.
-   Mekanisme penyimpanan token telah dievaluasi dan ditingkatkan jika
    diperlukan.
