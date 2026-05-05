# MUKIDI DKS-2 
**(Monitoring User Kamera Identification Detector Intruder)**

Sistem Keamanan CCTV Pintar berbasis **Kecerdasan Buatan (AI)** yang dapat mendeteksi wajah secara real-time, mengenali orang yang terdaftar, mencatat kehadiran, dan mendeteksi penyusup (wajah tak dikenal) secara akurat.

## 🌟 Fitur Utama
1. **Sistem Hybrid AI Terdepan**
   Menggabungkan *InsightFace* (untuk ekstraksi vektor wajah) dan *TensorFlow Neural Network* (untuk memastikan keakuratan klasifikasi meskipun hanya memiliki sampel foto yang sedikit menggunakan teknik *Data Augmentation*).
2. **Auto-Cleanup & Anti-Duplikasi**
   Sistem secara otomatis berjalan di latar belakang untuk merapikan data penyusup. Jika penyusup yang sama muncul lagi, sistem tidak akan membuat duplikat, melainkan akan menimpa foto lama dengan foto baru yang lebih tajam/jelas.
3. **Pendaftaran Wajah Mudah via Web UI**
   Anda tidak perlu mengerti kode untuk menambahkan orang baru. Cukup gunakan antarmuka Web UI, arahkan wajah ke kamera sesuai instruksi (Kiri, Kanan, Atas, Bawah, Tengah), dan sistem akan mempelajarinya.
4. **Latih Ulang (Retrain) Otomatis**
   Tombol "LATIH ULANG MODEL" tersedia di UI untuk memperbarui otak AI secara langsung di latar belakang tanpa harus mematikan kamera CCTV.

---

## 💻 Persyaratan Sistem
- Komputer / Laptop dengan OS Windows (dianjurkan Windows 10/11)
- Webcam atau IP Camera
- **Python 3.9 atau lebih baru** (Saat menginstal Python, pastikan Anda mencentang opsi **"Add Python to PATH"**)

---

## 🚀 Cara Instalasi & Menjalankan (Sangat Mudah!)

Anda tidak perlu mengetik perintah yang rumit. Ikuti langkah berikut:

1. Unduh atau salin seluruh folder proyek ini ke komputer Anda.
2. Buka folder proyek tersebut.
3. Cari file bernama **`Start_CCTV.bat`** lalu **Klik Dua Kali (Double-Click)**.
4. Jendela terminal hitam (Command Prompt) akan muncul. 
   - *Jika ini pertama kalinya*, sistem akan otomatis mengunduh dan menginstal semua library AI yang dibutuhkan (sekitar beberapa ratus MB). Pastikan koneksi internet Anda lancar.
   - *Jika instalasi sudah selesai*, sistem akan otomatis menyalakan kamera CCTV.
5. Buka Browser Anda (Google Chrome / Edge) dan ketik alamat:
   👉 **http://localhost:5000**
6. Selamat! Anda sudah masuk ke Panel Kontrol CCTV Anda.

---

## 📖 Panduan Penggunaan Panel Kontrol Web

- **Menambahkan Orang Baru**: 
  1. Di panel kiri, ketik nama orang pada kolom yang disediakan.
  2. Klik **MULAI DAFTARKAN**.
  3. Minta orang tersebut melihat ke arah kamera dan mengikuti instruksi posisi wajah di layar.
- **Melatih AI (Penting!)**: 
  Setelah Anda mendaftarkan satu atau beberapa wajah baru, klik tombol **LATIH ULANG MODEL**. Sistem TensorFlow akan memproses wajah tersebut agar lebih pintar membedakan mana yang dikenal dan mana yang penyusup.
- **Menghapus Duplikat & Memuat Ulang**:
  Tombol **RELOAD DATABASE** tidak hanya memuat ulang data, tetapi juga akan langsung memicu pembersihan folder penyusup (`unknown_detected`) untuk memastikan tidak ada wajah ganda.
- **Log Kehadiran**: 
  Setiap orang yang lewat, baik yang terdaftar maupun penyusup, akan dicatat secara mendetail beserta jam masuk dan jam keluarnya.

---

## 📂 Struktur Folder Penting
- `known_faces/` : Tempat menyimpan foto dan vektor wajah orang-orang yang sudah terdaftar.
- `unknown_detected/` : Tempat sistem memenjarakan (menyimpan foto) wajah penyusup yang tidak dikenali.
- `logs/` : Catatan aktivitas kehadiran harian (berbentuk file `.txt`).
- `app.py` : Mesin utama / server CCTV.
- `train_model.py` : Mesin TensorFlow untuk melatih AI wajah.
- `cleanup_unknowns.py` : Skrip pembersih wajah duplikat.

---
*MUKIDI DKS-2 - Keamanan yang Dapat Anda Andalkan.*
