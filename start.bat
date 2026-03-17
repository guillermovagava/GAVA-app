@echo off
echo ============================================================
echo  GAVA Recruitment CRM - Starting...
echo ============================================================
echo.

IF NOT EXIST .env (
    echo ERROR: .env file not found.
    echo Please run setup.bat first, then fill in your API keys.
    pause
    exit /b 1
)

echo Starting backend server...
start "GAVA Backend" cmd /k "cd backend && set PYTHONPATH=%CD% && uvicorn main:app --reload --port 8000"

timeout /t 2 /nobreak >nul

echo Starting frontend...
start "GAVA Frontend" cmd /k "cd frontend && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ============================================================
echo  App is running!
echo  Open your browser to: http://localhost:5173
echo.
echo  To stop the app: close the two terminal windows that opened.
echo ============================================================
echo.

REM Open browser automatically
start http://localhost:5173
