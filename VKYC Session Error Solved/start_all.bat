@echo off
echo Starting VKYC Application...
echo.
echo This will start both backend and frontend in separate windows.
echo.
echo Starting Backend (FastAPI) on port 8000...
start "VKYC Backend" cmd /k "cd backend && python main.py"
timeout /t 3 /nobreak >nul
echo.
echo Starting Frontend (Django) on port 8001...
start "VKYC Frontend" cmd /k "cd frontend && python manage.py runserver 8001"
echo.
echo Both servers are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:8001
echo.
pause

