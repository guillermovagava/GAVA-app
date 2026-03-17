@echo off
echo ============================================================
echo  GAVA Recruitment CRM - First-Time Setup
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python is not installed.
    echo Please download and install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Node.js is not installed.
    echo Please download and install Node.js LTS from https://nodejs.org/
    pause
    exit /b 1
)

echo [1/4] Installing Python backend dependencies...
cd backend
pip install -r requirements.txt
IF ERRORLEVEL 1 (
    echo ERROR: Failed to install Python dependencies.
    pause
    exit /b 1
)
cd ..

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

echo.
echo [3/4] Creating .env file from template...
IF NOT EXIST .env (
    copy .env.example .env
    echo .env file created. You MUST edit it with your API keys before running the app.
) ELSE (
    echo .env file already exists - skipping.
)

echo.
echo [4/4] Setup complete!
echo.
echo ============================================================
echo  NEXT STEPS:
echo  1. Open the file ".env" in Notepad and fill in your keys:
echo     - YELP_API_KEY
echo     - ANTHROPIC_API_KEY
echo     - GMAIL_ADDRESS
echo     - GMAIL_APP_PASSWORD
echo  2. Double-click "start.bat" to launch the app
echo  3. Open your browser to http://localhost:5173
echo ============================================================
echo.
pause
