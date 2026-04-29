# 📹 Face Recognition CCTV System

Sistem pengawasan CCTV berbasis web interaktif dengan kemampuan deteksi dan pengenalan wajah (*face recognition*) secara *real-time* menggunakan AI (InsightFace).

## ✨ Fitur Utama
* **Pemantauan Real-Time:** Akses kamera CCTV langsung dari browser Anda.
* **Deteksi Cerdas:** Sistem dapat membedakan wajah yang **TERDAFTAR** (Known) dan **PENYUSUP** (Unknown).
* **Auto-Capture Penyusup:** Wajah yang tidak dikenali akan otomatis difoto dan disimpan ke dalam sistem dengan nama ID (U1, U2, dst).
* **Registrasi Wajah via Web:** Daftarkan wajah orang baru langsung dari layar UI tanpa harus mengutak-atik folder (meminta user menghadap ke 5 arah: Atas, Bawah, Kiri, Kanan, Tengah).
* **Sistem Log & Sesi Aktif:** Mencatat waktu "MASUK" dan "KELUAR" untuk setiap wajah yang terdeteksi di kamera.
* **Ganti Kamera:** Mendukung penggunaan lebih dari 1 kamera (Webcam bawaan / USB WebCam).

---

## ⚙️ Persyaratan Sistem (Prerequisites)
Sebelum menjalankan program ini, pastikan PC/Laptop Anda sudah memiliki:
1. **OS Windows** (Terdapat file `.bat` khusus pengguna Windows).
2. **Kamera/Webcam** yang aktif.
3. **Koneksi Internet** (Hanya diperlukan saat pertama kali dijalankan untuk mengunduh library dan model AI).
4. **Python 3.x** terinstal. 
   > ⚠️ **SANGAT PENTING:** Saat menginstal Python, pastikan Anda mencentang kotak **"Add Python.exe to PATH"** di menu awal instalasi.

---

## 🚀 Cara Instalasi & Menjalankan Program (1-Click Run)

Anda **tidak perlu** mengetikkan kode instalasi library apa pun secara manual. Ikuti langkah mudah ini:

1. Klik tombol hijau **Code** di pojok kanan atas halaman ini, lalu pilih **Download ZIP**.
2. Ekstrak folder ZIP tersebut ke komputer Anda (misalnya di *Desktop* atau *Documents*).
3. Buka folder hasil ekstrak tersebut.
4. Klik dua kali (**Double-Click**) pada file `Jalankan_Program.bat`.
5. Jendela terminal hitam (CMD) akan terbuka. Pada **pemakaian pertama kali**, sistem akan otomatis membuat *Virtual Environment* dan mendownload semua library AI (seperti OpenCV, Flask, dan InsightFace). *Proses ini memakan waktu beberapa menit tergantung kecepatan internet Anda.*
6. Setelah muncul tulisan **"SISTEM SIAP! MENJALANKAN SERVER"**, buka browser Anda (Chrome/Edge/Firefox).
7. Ketikkan alamat ini di browser: **`http://localhost:5000`**

Sistem CCTV Anda siap digunakan! 

---

## 💡 Panduan Penggunaan Antarmuka (UI)
* **Mode CCTV:** Tekan tombol ini agar kamera mulai memantau dan mendeteksi wajah secara *real-time*.
* **Daftarkan Wajah:** Tekan tombol ini, masukkan nama user baru, lalu ikuti instruksi di layar untuk memindai wajah.
* **Reload Database:** Jika Anda menghapus atau menambah foto secara manual di dalam folder, tekan tombol ini agar sistem membaca ulang data terbaru.
* **Pop-Up Detail Wajah:** Anda dapat mengklik foto wajah yang muncul di daftar panel sebelah kanan untuk memperbesar gambar (*zoom-in*).

---

## 📂 Struktur Folder Otomatis
Sistem akan membuat beberapa folder secara otomatis saat program dijalankan:
* `env/` : Berisi sistem isolasi Python dan seluruh library pendukung (Jangan dihapus).
* `known_faces/` : Tempat database foto dan data numerik (*embedding*) wajah yang sudah diregistrasi.
* `unknown_detected/` : Tempat sistem menyimpan otomatis foto wajah penyusup/orang asing.
* `logs/` : File teks yang mencatat riwayat masuk/keluar harian.

---
*Dibuat menggunakan Python, Flask, OpenCV, dan InsightFace.*
