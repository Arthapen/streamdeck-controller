@echo off
title StreamDeck - Restart All
echo ==========================================
echo   StreamDeck - Restart All
echo ==========================================

echo [STOP] Deteniendo instancias previas...
call "%~dp0stop_todo.bat"

echo.
echo [START] Iniciando todo de nuevo...
call "%~dp0start_todo.bat"

echo.
echo [LISTO] Companion y Web reiniciados.
pause
