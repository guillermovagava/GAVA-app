@echo off
setlocal enabledelayedexpansion
title GAVA Recruiting — Build

echo.
echo  =========================================
echo    GAVA Recruiting — Build Script
echo  =========================================
echo.

:: ── Step 1: Build React frontend ─────────────────────────────────────────────
echo  [1/4]  Building React frontend...
cd frontend
call npm install --silent
call npm run build
if errorlevel 1 (
    echo.
    echo  ERROR: React build failed! Check errors above.
    pause & exit /b 1
)
cd ..
echo  Done.
echo.

:: ── Step 2: Copy build to backend/static ─────────────────────────────────────
echo  [2/4]  Copying frontend build to backend\static...
if exist "backend\static" rmdir /s /q "backend\static"
xcopy "frontend\dist" "backend\static" /s /e /i /q
echo  Done.
echo.

:: ── Step 3: Install Python dependencies ──────────────────────────────────────
echo  [3/4]  Installing Python dependencies...
py -3.12 -m pip install --quiet pyinstaller ^
    uvicorn[standard] fastapi sqlalchemy httpx aiosmtplib ^
    openpyxl anthropic python-dotenv beautifulsoup4 ^
    watchfiles
echo  Done.
echo.

:: ── Step 4: Package with PyInstaller ─────────────────────────────────────────
echo  [4/4]  Packaging with PyInstaller (this may take 2-5 minutes)...
py -3.12 -m PyInstaller ^
  --onedir ^
  --windowed ^
  --name "GAVA Recruiting" ^
  --add-data "backend;backend" ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols ^
  --hidden-import uvicorn.protocols.http ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.websockets ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.lifespan ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import email.mime.multipart ^
  --hidden-import email.mime.text ^
  --hidden-import aiosmtplib ^
  --hidden-import sqlalchemy.dialects.sqlite ^
  --hidden-import openpyxl ^
  --hidden-import anthropic ^
  --hidden-import httpx ^
  --hidden-import bs4 ^
  --noconfirm ^
  launcher.py

if errorlevel 1 (
    echo.
    echo  ERROR: PyInstaller failed! Check errors above.
    pause & exit /b 1
)

:: ── Copy .env to the output folder ───────────────────────────────────────────
echo.
echo  Copying .env to output folder...
if exist ".env" (
    copy ".env" "dist\GAVA Recruiting\.env" > nul
    echo  .env copied.
) else (
    echo  WARNING: .env not found — copy it manually to dist\GAVA Recruiting\.env
)

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  =========================================
echo    BUILD COMPLETE!
echo  =========================================
echo.
echo  Your app folder: dist\GAVA Recruiting\
echo.
echo  To run the app:
echo    Double-click: dist\GAVA Recruiting\GAVA Recruiting.exe
echo.
echo  Your leads database will be saved in the
echo  same folder as the .exe automatically.
echo.
pause
