# 🛠️ Panduan Instalasi Manual CCTV-DKS (Sangat Mudah!)

Halo! Panduan ini dibuat khusus untuk Anda yang masih sangat awam. Kita akan menggunakan **VS Code** agar prosesnya lebih mudah dipantau.

Ikuti langkah-langkah di bawah ini pelan-pelan ya.

---

## 📋 Persiapan (Wajib!)

### 1. Install Python 3.10
*   Download di sini: [Python 3.10.11](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe)
*   **PENTING**: Saat instal, **WAJIB CENTANG** kotak `Add Python 3.10 to PATH` sebelum klik *Install Now*. Jika lupa, program tidak akan jalan.

### 2. Install VS Code & Git
*   **VS Code**: [code.visualstudio.com](https://code.visualstudio.com/)
*   **Git**: [git-scm.com](https://git-scm.com/download/win) (Pilih Windows Setup). Ini gunanya untuk mendownload file project secara otomatis.

---

## 🚀 Langkah Instalasi (Lewat VS Code)

### 1. Mendownload File Project (Git Clone)
1.  Buka **Visual Studio Code**.
2.  Klik menu **Terminal** > **New Terminal**.
3.  Di jendela Terminal (bagian bawah), ketik perintah ini untuk mengambil semua file program:
    ```powershell
    git clone https://github.com/Kururu1/CCTV-DKS.git
    ```
4.  Setelah selesai, klik menu **File** > **Open Folder...**.
5.  Pilih folder bernama `CCTV-DKS` yang baru saja muncul.
6.  Klik **Select Folder**.

### 2. Buka Terminal Baru di Dalam Folder
Setelah folder terbuka, kita harus membuka Terminal lagi agar posisinya benar di dalam folder project:
1.  Klik menu **Terminal** > **New Terminal**.
2.  Pastikan di sebelah kiri kursor Terminal muncul tulisan `...\CCTV-DKS>`.

### 3. Membuat Lingkungan Virtual (Virtual Environment)
Ketik perintah di bawah ini dan tekan **Enter**:
```powershell
python -m venv venv
```
*Tunggu sebentar sampai muncul folder baru bernama `venv` di daftar file sebelah kiri.*

### 4. Mengaktifkan Lingkungan (v-env)
Salin perintah ini ke Terminal dan tekan **Enter**:
```powershell
.\venv\Scripts\activate
```
*Jika berhasil, Anda akan melihat tulisan `(venv)` berwarna hijau/biru di awal baris Terminal.*

### 5. Menginstal Bahan-Bahan (Requirements)
Ketik perintah ini untuk mendownload semua kebutuhan AI-nya (Pastikan internet Anda nyala):
```powershell
pip install -r requirements.txt
```
*Proses ini memakan waktu beberapa menit. Tunggu sampai muncul baris baru dan tulisan `Successfully installed...`.*

---

## 🧠 Langkah Terakhir: Menjalankan Program

### 6. Melatih Otak AI (Training)
Agar program bisa mengenali wajah, kita harus melatihnya dulu. Ketik:
```powershell
python train_model.py
```
*Tunggu sampai selesai (muncul tulisan "Model saved").*

### 7. Menyalakan CCTV
Terakhir, ketik perintah ini untuk menyalakan aplikasinya:
```powershell
python app.py
```
*   Jika muncul tulisan `Running on http://127.0.0.1:5000`, artinya sukses!
*   Buka Google Chrome atau Edge, lalu buka alamat: **http://localhost:5000**

---

## 💡 Tips untuk Pemula
*   **Copy-Paste**: Di Terminal VS Code, Anda bisa copy teks di sini dan paste di Terminal dengan cara **Klik Kanan** pada mouse di area terminal.
*   **Jika Gagal Clone**: Jika `git clone` sulit, Anda bisa download manual via tombol hijau **"Code"** > **"Download ZIP"** di link GitHub tersebut, lalu ekstrak dan buka foldernya di VS Code.
*   **Matikan Program**: Untuk mematikan program, klik di area Terminal lalu tekan tombol **Ctrl + C** di keyboard secara bersamaan.

---
