@echo off
TITLE CCTV DKS-2 Auto Installer & Launcher
COLOR 0A

echo ===================================================
echo   MUKIDI DKS-2 (CCTV FACE RECOGNITION SYSTEM)
echo ===================================================
echo.

:: Cek apakah Python sudah terinstal
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python tidak ditemukan di komputer ini!
    echo Silakan install Python terlebih dahulu (https://www.python.org/downloads/)
    echo Pastikan Anda mencentang opsi "Add Python to PATH" saat instalasi.
    pause
    exit /b
)

:: Cek apakah folder venv sudah ada
IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [*] Virtual Environment belum ada. Sedang membuat virtual environment (venv)...
    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Gagal membuat virtual environment!
        pause
        exit /b
    )
    echo [*] Virtual Environment berhasil dibuat!
)

:: Mengaktifkan virtual environment
echo [*] Mengaktifkan virtual environment...
call venv\Scripts\activate.bat

:: Menginstal/Memperbarui dependensi
echo [*] Memeriksa dan menginstal library yang dibutuhkan (silakan tunggu jika ini pertama kalinya)...
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt

:: Menjalankan aplikasi
echo.
echo ===================================================
echo    MEMULAI SISTEM CCTV... JANGAN TUTUP JENDELA INI
echo    Buka Web Browser ke: http://localhost:5000
echo ===================================================
echo.
python app.py

:: Jika aplikasi berhenti
pause
