@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title AI Nutrition Analyzer - Web Server

echo ============================================================
echo   AI NUTRITION ANALYZER - KHOI DONG WEBSITE
echo ============================================================
echo.

set "PY=%~dp0.venv\Scripts\python.exe"

REM ---------- 1. Kiem tra moi truong ao ----------
if not exist "%PY%" (
  echo [!] Chua co moi truong ao .venv
  echo [1/3] Dang tao moi truong va cai dat thu vien ^(co the mat 5-15 phut^)...
  call "%~dp0scripts\setup_env.bat"
  if errorlevel 1 (
    echo [X] Cai dat that bai. Xem thong bao phia tren.
    pause
    exit /b 1
  )
)

REM ---------- 2. Kiem tra file .env ----------
if not exist "%~dp0.env" (
  echo [i] Chua co .env - tao tu .env.example
  copy /y "%~dp0.env.example" "%~dp0.env" >nul
  echo [i] Da tao .env. Nen mo file nay va dien SECRET_KEY.
)

REM ---------- 3. Kiem tra database ----------
if not exist "%~dp0data\nutrition.db" (
  echo [2/3] Chua co database - dang khoi tao ^(migration + du lieu mau^)...
  call "%~dp0scripts\init_db.bat"
  if errorlevel 1 (
    echo [X] Khoi tao database that bai.
    pause
    exit /b 1
  )
)

REM ---------- 4. Kiem tra Ollama (khong bat buoc) ----------
echo [3/3] Kiem tra Ollama tai http://127.0.0.1:11434 ...
curl -s -o nul -m 3 http://127.0.0.1:11434/api/tags
if errorlevel 1 (
  echo [i] Ollama khong chay. Website van hoat dong, rieng tro ly AI se bao khong kha dung.
) else (
  echo [v] Ollama dang chay.
)

echo.
echo Dang khoi dong web server...
echo.
"%PY%" run.py %*
set "RC=%ERRORLEVEL%"
echo.
echo Server da dung ^(exit code %RC%^).
pause
endlocal
