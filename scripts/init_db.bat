@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
title Init database - AI Nutrition Analyzer

set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [X] Chua co .venv. Chay scripts\setup_env.bat truoc.
  pause
  exit /b 1
)

echo [1/2] Chay migration Alembic ...
"%PY%" -m alembic upgrade head
if errorlevel 1 (
  echo [!] Neu day la lan dau va chua co revision, hay tao revision truoc:
  echo     .venv\Scripts\python.exe -m alembic revision --autogenerate -m "init schema"
  pause
  exit /b 1
)

echo.
echo [2/2] Nap danh muc chat dinh duong + nguon du lieu co ban ...
"%PY%" scripts\seed_reference_data.py
if errorlevel 1 (
  echo [X] Seed that bai.
  pause
  exit /b 1
)

echo.
echo [v] Database san sang: data\nutrition.db
pause
endlocal
