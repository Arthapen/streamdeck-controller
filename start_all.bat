@echo off
echo ================================
echo   Iniciando StreamDeck Controller V2
echo ================================

REM Launch Backend
start "BACKEND" cmd /k "cd /d %~dp0companion && ..\.venv\Scripts\activate.bat && python main.py"

REM Launch Frontend
start "FRONTEND" cmd /k "cd /d %~dp0web-client && ..\.venv\Scripts\activate.bat && python -m http.server 8080 --bind 0.0.0.0"

echo Servicios iniciados. 
echo Ve a: http://127.0.0.1:8080/
pause
