# 🤖 MUKIDI — Modul Pembelajaran Sistem Pengenalan Wajah Berbasis AI

> **MUKIDI** = (Monitoring User Kamera Identification Detector Intruder)  
> Sistem cerdas yang dapat mengenali wajah manusia secara otomatis menggunakan kecerdasan buatan (AI).

---

## 📚 Daftar Isi

1. [Apa itu MUKIDI?](#1-apa-itu-mukidi)
2. [Cara Kerja Sistem Secara Umum](#2-cara-kerja-sistem-secara-umum)
3. [Komponen Utama Sistem](#3-komponen-utama-sistem)
4. [Alur Data: Dari Kamera ke Layar](#4-alur-data-dari-kamera-ke-layar)
5. [Mode Operasi](#5-mode-operasi)
6. [Fitur Pendaftaran Wajah (SCAN)](#6-fitur-pendaftaran-wajah-scan)
7. [Fitur Pengenalan Wajah (RUN)](#7-fitur-pengenalan-wajah-run)
8. [Kontrol Kamera (PTZ)](#8-kontrol-kamera-ptz)
9. [Teknologi yang Digunakan](#9-teknologi-yang-digunakan)
10. [Arsitektur Sistem](#10-arsitektur-sistem)
11. [Keamanan & Logging](#11-keamanan--logging)
12. [Istilah Penting (Glosarium)](#12-istilah-penting-glosarium)
13. [Pertanyaan Umum (FAQ)](#13-pertanyaan-umum-faq)

---

## 1. Apa itu MUKIDI?

MUKIDI adalah sebuah **sistem keamanan berbasis pengenalan wajah**. Bayangkan seperti satpam pintar yang bisa mengenali wajah setiap orang yang melintas di depan kamera, lalu mencatatnya secara otomatis.

### 🎯 Fungsi Utama:
- **Mengenali orang yang sudah terdaftar** → ditampilkan nama mereka
- **Mendeteksi orang asing** → dicatat sebagai "Unknown" atau diberi kode seperti `U1`, `U2`, dst.
- **Mencatat aktivitas masuk dan keluar** → tersimpan dalam log harian
- **Bisa diakses dari browser** → tampilan web yang modern dan mudah digunakan

### 🏗️ Gambaran Besar:
```
[Kamera] ──► [Server Python] ──► [AI Deteksi Wajah] ──► [Tampilan Web]
                                         │
                                  [Database Wajah]
```

---

## 2. Cara Kerja Sistem Secara Umum

Sistem MUKIDI bekerja seperti mata manusia yang sangat cepat dan tidak pernah lupa wajah seseorang.

### Langkah-langkah Proses:

**Langkah 1 — Tangkap Gambar**  
Kamera merekam video secara terus-menerus. Setiap beberapa milidetik, sistem mengambil satu frame (gambar diam) dari video tersebut.

**Langkah 2 — Cari Wajah**  
AI mencari apakah ada wajah manusia di dalam gambar. Jika ada, AI menandai posisinya (kotak di sekitar wajah).

**Langkah 3 — Buat "Sidik Jari Wajah"**  
Setiap wajah diubah menjadi sekumpulan angka unik (disebut **embedding** atau **vektor**). Ini seperti sidik jari — setiap orang punya pola yang berbeda.

**Langkah 4 — Cocokkan dengan Database**  
Sistem membandingkan "sidik jari wajah" yang baru ditangkap dengan semua wajah yang ada di database. Jika cocok → nama orang tersebut ditampilkan.

**Langkah 5 — Tampilkan Hasil**  
Hasil pengenalan ditampilkan di layar: nama, kotak wajah, dan status (terdaftar atau penyusup).

---

## 3. Komponen Utama Sistem

### 🖥️ A. Backend (Otak Sistem) — `app.py`

File `app.py` adalah "otak" dari seluruh sistem. Di sinilah semua proses AI dan logika berjalan.

**Bagian-bagian penting dalam app.py:**

| Bagian | Fungsi |
|--------|--------|
| `FaceAnalysis` | Model AI untuk mendeteksi dan menganalisis wajah |
| `Flask` | Server web yang menghubungkan backend dengan tampilan |
| `cap` (VideoCapture) | Menangkap video dari kamera |
| `known_db` | Database wajah orang yang sudah terdaftar |
| `unknown_db` | Database wajah orang asing yang pernah terdeteksi |
| `ptz_state` | Pengaturan pergerakan kamera (pan, tilt, zoom) |

### 🌐 B. Frontend (Tampilan) — `index.html`

File `index.html` adalah tampilan yang kita lihat di browser. Dibuat dengan desain futuristik berwarna biru-hitam.

**Elemen tampilan utama:**

| Elemen | Fungsi |
|--------|--------|
| Panel Kiri | Menu kontrol dan pengaturan |
| Tengah (Kamera) | Tampilan live video dengan deteksi wajah |
| Panel Kanan | Log aktivitas dan informasi real-time |
| Header | Status sistem dan jam |

---

## 4. Alur Data: Dari Kamera ke Layar

Berikut adalah perjalanan data dari kamera hingga muncul di layar:

```
┌─────────────────────────────────────────────────────────────┐
│                    ALUR KERJA MUKIDI                        │
│                                                             │
│  📷 KAMERA                                                  │
│      │                                                       │
│      ▼                                                       │
│  🔲 Ambil Frame (gambar per detik)                          │
│      │                                                       │
│      ▼                                                       │
│  🤖 AI Deteksi Wajah (InsightFace buffalo_l)               │
│      │                                                       │
│      ├──── Tidak ada wajah? → Lanjutkan ke frame berikutnya │
│      │                                                       │
│      ▼                                                       │
│  📊 Buat Embedding (512 angka unik per wajah)              │
│      │                                                       │
│      ▼                                                       │
│  🔍 Cocokkan dengan Database                                │
│      │                                                       │
│      ├──── Cocok (skor > 0.35)? → Tampilkan NAMA           │
│      ├──── Orang Asing Dikenal? → Tampilkan KODE (U1, U2) │
│      └──── Benar-benar Asing? → Tampilkan "Unknown"        │
│      │                                                       │
│      ▼                                                       │
│  📝 Catat di Log Harian                                     │
│      │                                                       │
│      ▼                                                       │
│  🖥️ Kirim ke Browser (via API Flask)                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Mode Operasi

Sistem MUKIDI memiliki 4 mode utama:

### 🔴 IDLE (Berhenti)
Sistem menyala tapi tidak melakukan pengenalan wajah. Kamera tetap aktif tapi tidak ada proses AI yang berjalan secara intensif.

### 🟡 WAIT_CONFIRM (Menunggu Konfirmasi)
Sistem siap untuk mendaftarkan wajah baru. Layar menampilkan nama yang akan didaftarkan dan menunggu pengguna menekan tombol "Mulai Scan".

### 🟡 SCAN (Mendaftarkan Wajah)
Sistem sedang mengambil foto wajah dari berbagai sudut. Pengguna diminta untuk menghadapkan wajah ke 5 arah berbeda.

### 🟢 RUN (Berjalan / Pengenalan Aktif)
Mode utama. Sistem aktif mengenali semua wajah yang masuk ke frame kamera secara real-time.

---

## 6. Fitur Pendaftaran Wajah (SCAN)

Untuk bisa dikenali oleh sistem, seseorang harus terlebih dahulu **didaftarkan**. Proses ini disebut "scan".

### Langkah Pendaftaran:

**1. Masukkan Nama**  
Pengguna mengetik nama orang yang akan didaftarkan di panel kontrol.

**2. Sistem Minta 5 Posisi Wajah**  
Sistem akan meminta orang tersebut menghadapkan wajah ke berbagai arah:
- ⬆️ **ATAS** — mendongak ke atas
- ⬇️ **BAWAH** — menunduk ke bawah  
- ⬅️ **KIRI** — melihat ke kiri
- ➡️ **KANAN** — melihat ke kanan
- 🎯 **CENTER** — menghadap lurus ke depan

**3. Stabilisasi Posisi**  
Sistem tidak langsung mengambil foto. Ia menunggu posisi wajah stabil selama beberapa frame (sekitar 15 frame = ~0.5 detik) sebelum mengambil gambar.

**4. Simpan Data**  
Setiap posisi yang berhasil disimpan sebagai:
- File gambar `.jpg` — foto wajah
- File `.npy` — data embedding (angka-angka unik wajah)

**5. Selesai**  
Setelah 5 posisi terkumpul, sistem otomatis memuat ulang database dan siap mengenali orang tersebut.

### Mengapa 5 Posisi?
Wajah manusia terlihat berbeda dari berbagai sudut. Dengan mendaftarkan 5 posisi, sistem bisa mengenali seseorang meskipun mereka tidak selalu menghadap lurus ke kamera.

---

## 7. Fitur Pengenalan Wajah (RUN)

Saat mode RUN aktif, sistem terus-menerus menganalisis setiap wajah yang terdeteksi.

### Proses Pengenalan:

**A. Hitung Skor Kemiripan**  
Sistem menggunakan rumus matematika bernama **Cosine Similarity** untuk mengukur seberapa mirip dua wajah. Skor berkisar dari 0 (tidak mirip sama sekali) hingga 1 (identik sempurna).

```
Skor > 0.35 → Wajah dikenali (orang terdaftar)
Skor 0.25–0.35 → Mungkin sama orang (orang asing yang pernah masuk)  
Skor < 0.25 → Benar-benar orang asing baru
```

**B. Konfirmasi dengan TensorFlow (Opsional)**  
Jika model TensorFlow tersedia, sistem menggunakannya sebagai "pendapat kedua" untuk meningkatkan akurasi pengenalan. Sistem menggabungkan dua hasil (40% dari cosine, 60% dari TensorFlow).

**C. Klasifikasi Orang**  

| Tipe | Warna Kotak | Keterangan |
|------|-------------|------------|
| **TERDAFTAR** | 🟢 Hijau | Orang yang sudah didaftarkan |
| **PENYUSUP (Orang Asing Dikenal)** | 🟠 Oranye | Pernah masuk sebelumnya, belum terdaftar resmi |
| **UNKNOWN** | 🔴 Merah | Benar-benar orang asing baru |

**D. Pencatatan Kehadiran**  
Setiap orang yang masuk dan keluar dari frame kamera dicatat otomatis dengan:
- Nama/kode orang
- Waktu masuk
- Waktu keluar
- Status (Terdaftar / Penyusup)

---

## 8. Kontrol Kamera (PTZ)

PTZ adalah singkatan dari **Pan** (gerak kiri-kanan), **Tilt** (gerak atas-bawah), dan **Zoom** (perbesar/perkecil gambar).

### Dua Mode PTZ:

**🔧 Hardware PTZ**  
Untuk kamera yang mendukung pergerakan fisik (seperti Logitech Rally). Kamera benar-benar bergerak secara mekanis.

**💻 Software PTZ**  
Untuk kamera biasa (webcam). Sistem memotong dan memperbesar bagian dari gambar secara digital — kamera tidak bergerak fisik, tapi gambar yang ditampilkan berubah seolah kamera bergerak.

### Cara Mengontrol PTZ:

**Menggunakan Tombol di UI:**
- Tombol panah (↑↓←→) di panel kontrol

**Menggunakan Keyboard:**
- `←` `→` `↑` `↓` — Gerakkan pandangan
- `+` / `=` — Perbesar (Zoom In)
- `-` / `_` — Perkecil (Zoom Out)
- `H` — Reset ke posisi awal

---

## 9. Teknologi yang Digunakan

### 🤖 Kecerdasan Buatan (AI)

**InsightFace (buffalo_l)**  
Model AI utama untuk mendeteksi dan menganalisis wajah. Model ini sudah terlatih dengan jutaan foto wajah dari seluruh dunia. Ia bisa mendeteksi wajah, menentukan arah pandangan, dan menghasilkan embedding.

**TensorFlow**  
Framework AI tambahan yang digunakan untuk model klasifikasi sekunder. Meningkatkan akurasi pengenalan dengan cara "voting" antara dua model.

### 🐍 Python & Library

| Library | Kegunaan |
|---------|---------|
| `OpenCV (cv2)` | Membaca video dari kamera, menggambar kotak pada wajah |
| `Flask` | Membuat server web agar browser bisa berkomunikasi dengan Python |
| `NumPy` | Operasi matematika pada data wajah (array angka) |
| `InsightFace` | Model AI deteksi & pengenalan wajah |
| `TensorFlow` | Model AI sekunder untuk klasifikasi |

### 🌐 Web (HTML/CSS/JavaScript)

- **HTML** — Struktur halaman
- **CSS** — Tampilan visual futuristik (tema gelap, efek neon)
- **JavaScript** — Interaktivitas real-time (update status, polling data dari server)
- **Font Orbitron & Rajdhani** — Font khas sci-fi untuk tampilan

### ⚡ Akselerasi GPU

Sistem mendukung **NVIDIA GPU** untuk mempercepat proses AI. Tanpa GPU, sistem berjalan di CPU (lebih lambat tapi tetap berfungsi). Saat startup, sistem otomatis mencari dan mengonfigurasi driver GPU (CUDA).

---

## 10. Arsitektur Sistem

### Komunikasi Client-Server

```
┌─────────────────────────────────────────────────────────────┐
│  BROWSER (index.html)                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Panel Kiri  │  │ Live Camera  │  │   Panel Kanan    │  │
│  │  (Kontrol)   │  │  (Streaming) │  │   (Log & Info)   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                 │                    │             │
└─────────┼─────────────────┼────────────────────┼────────────┘
          │ HTTP Request     │ MJPEG Stream        │ Polling
          ▼                 ▼                    ▼
┌─────────────────────────────────────────────────────────────┐
│  SERVER PYTHON (app.py) — Flask                             │
│                                                             │
│  /command  /video_feed  /state  /register  /ptz  dll.      │
│                                                             │
│  ┌───────────────┐   ┌────────────┐   ┌─────────────────┐  │
│  │  AI Engine    │   │  Database  │   │  PTZ Controller │  │
│  │ InsightFace   │   │  known_db  │   │  pan/tilt/zoom  │  │
│  │ TensorFlow    │   │ unknown_db │   │                 │  │
│  └───────────────┘   └────────────┘   └─────────────────┘  │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  📷 Kamera (OpenCV VideoCapture)                       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints (Titik Komunikasi)

| Endpoint | Metode | Fungsi |
|----------|--------|--------|
| `/video_feed` | GET | Stream video langsung dari kamera |
| `/state` | GET | Ambil status sistem terkini |
| `/command` | POST | Kirim perintah (mulai scan, stop, dll.) |
| `/register_upload` | POST | Daftarkan wajah dari file gambar/video |
| `/ptz` | POST | Kontrol pergerakan kamera |
| `/toggle_provider` | POST | Ganti antara GPU dan CPU |
| `/shutdown` | POST | Matikan sistem |

---

## 11. Keamanan & Logging

### 📋 Log Harian

Sistem secara otomatis mencatat semua aktivitas dalam file log harian. Setiap catatan berisi:
- **Nama/Kode** orang yang terdeteksi
- **Status** (Terdaftar / Penyusup)
- **Aksi** (Masuk / Keluar)
- **Waktu** kejadian

### 🔄 Sistem Cooldown

Untuk menghindari catatan duplikat, sistem menggunakan **cooldown**. Seseorang baru dicatat sebagai "KELUAR" jika sudah tidak terdeteksi selama beberapa detik (bukan langsung saat keluar frame sebentar).

### 🧹 Pembersihan Otomatis

Sistem memiliki modul `cleanup_unknowns` yang secara berkala membersihkan data orang asing yang mungkin sama tapi tercatat terpisah, untuk menjaga database tetap efisien.

### 📸 Kualitas Foto Otomatis

Saat menyimpan foto orang asing, sistem selalu mengecek **blur score** (seberapa tajam foto). Foto yang buram akan diganti dengan foto yang lebih tajam saat tersedia.

---

## 12. Istilah Penting (Glosarium)

| Istilah | Penjelasan Sederhana |
|---------|---------------------|
| **AI (Artificial Intelligence)** | Kecerdasan buatan — komputer yang bisa berpikir dan belajar |
| **Embedding** | "Sidik jari digital" wajah — sekumpulan angka yang merepresentasikan wajah unik seseorang |
| **Cosine Similarity** | Cara mengukur kemiripan dua wajah menggunakan matematika |
| **Frame** | Satu gambar diam dalam video (seperti satu foto) |
| **Database** | Tempat penyimpanan data (kumpulan wajah yang sudah terdaftar) |
| **Backend** | Bagian "belakang layar" sistem — kode Python yang memproses data |
| **Frontend** | Bagian yang terlihat pengguna — tampilan web di browser |
| **API** | Jembatan komunikasi antara browser dan server Python |
| **CUDA** | Teknologi NVIDIA untuk mempercepat AI menggunakan kartu grafis (GPU) |
| **PTZ** | Pan-Tilt-Zoom — kemampuan kamera untuk bergerak dan memperbesar gambar |
| **Buffer** | Tempat sementara untuk menyimpan data sebelum diproses |
| **Streaming** | Video yang ditampilkan secara langsung (live) tanpa jeda download |
| **Threshold** | Batas nilai — jika skor di atas batas ini, wajah dianggap cocok |
| **MJPEG** | Format streaming video yang digunakan sistem ini |

---

## 13. Pertanyaan Umum (FAQ)

**❓ Apakah sistem bisa mengenali wajah dengan masker?**  
Kemampuan ini tergantung pada model AI yang digunakan. Model buffalo_l dari InsightFace memiliki kemampuan terbatas untuk wajah yang tertutup sebagian.

**❓ Berapa banyak wajah yang bisa didaftarkan?**  
Tidak ada batas khusus. Namun semakin banyak wajah, sistem membutuhkan waktu sedikit lebih lama untuk pencocokan.

**❓ Apakah data wajah tersimpan di cloud?**  
Tidak. Semua data tersimpan secara lokal di komputer yang menjalankan sistem.

**❓ Apa yang terjadi jika GPU tidak tersedia?**  
Sistem otomatis beralih ke CPU. Kecepatan pemrosesan akan lebih lambat, tapi sistem tetap berfungsi normal.

**❓ Bagaimana cara menghapus wajah yang terdaftar?**  
Hapus folder yang berisi data wajah tersebut dari database, lalu muat ulang database melalui tombol "Reload DB".

**❓ Apakah sistem bisa diakses dari komputer lain?**  
Ya, selama komputer tersebut terhubung ke jaringan yang sama dan mengakses alamat IP server dengan port yang benar.

---

## 🎓 Ringkasan

MUKIDI adalah sistem pengenalan wajah yang menggabungkan:
1. **Kamera** → menangkap gambar
2. **AI (InsightFace)** → mendeteksi dan menganalisis wajah
3. **Database** → menyimpan dan mencocokkan wajah
4. **Web Server (Flask)** → menghubungkan semua komponen
5. **Browser (HTML)** → menampilkan hasil ke pengguna

Sistem ini dapat digunakan untuk berbagai keperluan seperti absensi otomatis, keamanan gedung, atau monitoring area tertentu — semua berjalan secara real-time tanpa perlu intervensi manual.

---

*Modul ini dibuat untuk membantu memahami cara kerja sistem MUKIDI secara umum tanpa perlu latar belakang teknis khusus.*
