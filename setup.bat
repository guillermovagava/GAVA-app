@echo off
echo ============================================================
echo  GAVA Recruitment CRM - First-Time Setup
echo ============================================================
echo.

REM ── Check for Python 3.12 specifically ──────────────────────
py -3.12 --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo.
    echo ERROR: Python 3.12 is not installed.
    echo.
    echo You appear to have a different version of Python, but this app
    echo requires Python 3.12 because some packages are not yet compatible
    echo with newer versions.
    echo.
    echo Please do the following:
    echo   1. Go to: https://www.python.org/downloads/release/python-3128/
    echo   2. Scroll down and click: "Windows installer (64-bit)"
    echo   3. Run the installer
    echo   4. IMPORTANT: Check the box that says "Add Python to PATH"
    echo   5. Click "Install Now"
    echo   6. Once done, run this setup.bat again
    echo.
    pause
    exit /b 1
)

FOR /F "tokens=*" %%i IN ('py -3.12 --version') DO SET PYTHON_VER=%%i
echo Using %PYTHON_VER%
echo.

REM ── Check Node.js ────────────────────────────────────────────
node --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Node.js is not installed.
    echo Please download and install Node.js LTS from https://nodejs.org/
    pause
    exit /b 1
)

REM ── Install Python backend dependencies ───────────────────────
echo [1/4] Installing Python backend dependencies...
cd backend
py -3.12 -m pip install --upgrade pip --quiet
py -3.12 -m pip install -r requirements.txt
IF ERRORLEVEL 1 (
    echo.
    echo ERROR: Failed to install Python dependencies.
    echo Please send a screenshot of this error for help.
    pause
    exit /b 1
)
cd ..

REM ── Install frontend dependencies ─────────────────────────────
echo.
echo [2/4] Installing frontend dependencies...
cd frontend
call npm install
IF ERRORLEVEL 1 (
    echo ERROR: Failed to install frontend dependencies.
    pause
    exit /b 1
)
cd ..

REM ── Create .env from template ──────────────────────────────────
echo.
echo [3/4] Creating .env file from template...
IF NOT EXIST .env (
    copy .env.example .env
    echo .env file created. You MUST edit it with your API keys before running the app.
) ELSE (
    echo .env file already exists - skipping.
)

REM ── Done ───────────────────────────────────────────────────────
echo.
echo [4/4] Setup complete!
echo.
echo ============================================================
echo  NEXT STEPS:
echo  1. Open the file ".env" in Notepad and fill in your keys:
echo     - GOOGLE_PLACES_API_KEY
echo     - HUNTER_API_KEY
echo     - ANTHROPIC_API_KEY
echo     - GMAIL_ADDRESS
echo     - GMAIL_APP_PASSWORD
echo  2. Double-click "start.bat" to launch the app
echo  3. Open your browser to http://localhost:5173
echo ============================================================
echo.
pause
