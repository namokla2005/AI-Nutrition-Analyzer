@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
title Setup environment - AI Nutrition Analyzer

echo ============================================================
echo   TAO MOI TRUONG AO .venv VA CAI DAT THU VIEN
echo ============================================================

REM Python 3.12 (torch/torchvision/sklearn on dinh nhat tren may nay)
set "PY312=C:\Users\Nam\AppData\Local\Programs\Python\Python312\python.exe"
if not exist "%PY312%" (
  echo [X] Khong tim thay Python 3.12 tai %PY312%
  echo     Hay sua bien PY312 trong file nay cho dung duong dan.
  pause
  exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
  echo [X] Khong tim thay 'uv'. Cai bang:  winget install astral-sh.uv
  echo     ^(Hoac thay bang: "%PY312%" -m venv .venv  roi  .venv\Scripts\python.exe -m pip install -r requirements.txt^)
  pause
  exit /b 1
)

echo [1/3] Tao .venv bang Python 3.12 ...
uv venv --python "%PY312%" .venv
if errorlevel 1 goto :err

set "PY=%~dp0..\.venv\Scripts\python.exe"

echo.
echo [2/3] Cai dat thu vien web + ML ^(scikit-learn, pandas, fastapi, sqlalchemy...^) ...
uv pip install --python "%PY%" fastapi "uvicorn[standard]" python-multipart jinja2 aiofiles httpx itsdangerous argon2-cffi email-validator pydantic pydantic-settings sqlalchemy alembic numpy pandas scikit-learn joblib pillow matplotlib pytest pytest-asyncio
if errorlevel 1 goto :err

echo.
echo [3/3] Cai dat PyTorch ban CPU ^(khong dung CUDA: GPU Quadro P2000 la sm_61^) ...
uv pip install --python "%PY%" --reinstall --no-deps --index-strategy unsafe-best-match ^
  torch==2.5.1+cu121 torchvision==0.20.1+cu121 --index-url https://download.pytorch.org/whl/cu121
REM Ban cu121 la kenh CUDA cuoi con ho tro Quadro P2000 (Pascal sm_61); cac ban moi hon da bo Pascal.
REM Neu may khong co GPU NVIDIA: doi --index-url thanh https://download.pytorch.org/whl/cpu va bo phan phien ban.
if errorlevel 1 goto :err

echo.
echo [v] Kiem tra nhanh:
"%PY%" -c "import fastapi, sqlalchemy, sklearn, pandas, torch, torchvision, argon2; print('OK', fastapi.__version__, sqlalchemy.__version__, sklearn.__version__, torch.__version__)"
echo.
echo [v] Hoan tat. Chay START_WEBSITE.bat de khoi dong website.
pause
exit /b 0

:err
echo.
echo [X] Co loi trong qua trinh cai dat.
pause
exit /b 1
