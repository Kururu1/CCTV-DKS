@echo off
title Face Recognition System Startup
color 0A

echo ===================================================
echo     MEMULAI SISTEM FACE RECOGNITION CCTV
echo ===================================================
echo.

:: Cek apakah Python sudah terinstal
python --version >nul 2>&1
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] Python tidak ditemukan di PC ini!
    echo Silakan install Python terlebih dahulu (jangan lupa centang "Add Python to PATH" saat instalasi).
    echo.
    pause
    exit
)

:: Cek apakah Virtual Environment (env) sudah ada
if not exist "env\" (
    echo [INFO] Menyiapkan lingkungan sistem untuk pertama kali...
    echo [INFO] Proses ini memakan waktu beberapa menit. Jangan tutup jendela ini.
    python -m venv env
)

:: Aktifkan Virtual Environment
call env\Scripts\activate

:: Cek apakah requirements.txt ada
if exist "requirements.txt" (
    echo [INFO] Memeriksa dan menginstal library yang dibutuhkan...
    :: Upgrade pip agar instalasi lebih lancar
    python -m pip install --upgrade pip >nul 2>&1
    :: Install library dari requirements.txt
    pip install -r requirements.txt
) else (
    color 0E
    echo [WARNING] File requirements.txt tidak ditemukan!
    echo Sistem akan mencoba menjalankan program dengan library yang ada.
    echo.
)

echo.
echo ===================================================
echo   SISTEM SIAP! MENJALANKAN SERVER DAN KAMERA...
echo ===================================================
echo [INFO] Buka http://localhost:5000 di browser Anda setelah teks "SISTEM AKTIF" muncul.
echo.

:: Jalankan file Python utama
:: (Pastikan nama file di bawah ini sama dengan nama file Python Anda)
python face_recog_server.py

:: Jika program berhenti atau crash, jendela terminal tidak langsung tertutup
pause