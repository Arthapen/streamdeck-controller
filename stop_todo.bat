@echo off
title StreamDeck - Stop All
echo ==========================================
echo   StreamDeck - Stop All
echo ==========================================
echo.

REM Cerramos las ventanas que abrimos con START (por título)
taskkill /F /FI "WINDOWTITLE eq StreamDeck Companion*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq StreamDeck Web*" >nul 2>&1

REM De paso matamos procesos python.exe que estén escuchando en 8765 o 8080
for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r ":8765[ ]" ^| findstr LISTENING') do (
    echo Cerrando proceso en puerto 8765 (PID %%p)...
    taskkill /PID %%p /F >nul 2>&1
)

for /f "tokens=5" %%p in ('netstat -ano ^| findstr /r ":8080[ ]" ^| findstr LISTENING') do (
    echo Cerrando proceso en puerto 8080 (PID %%p)...
    taskkill /PID %%p /F >nul 2>&1
)

echo.
echo [LISTO] Servicios detenidos.
pause
