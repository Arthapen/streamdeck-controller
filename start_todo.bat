@echo off
setlocal ENABLEDELAYEDEXPANSION
title StreamDeck - Start All

REM Detect base folders dynamically relative to this BAT
set COMP=%~dp0companion
for %%I in ("%COMP%\..") do set BASE=%%~fI
set WEB=%BASE%\web-client

echo ==========================================
echo   StreamDeck - Start All (MVP)
echo   Carpeta base: %BASE%
echo ==========================================
echo.

cd /d "%COMP%"
if not exist ".venv" (
  echo [VENV] Creando entorno virtual...
  py -3 -m venv .venv
)
echo [VENV] Activando entorno virtual...
call ".venv\Scripts\activate" || (
  echo [ERROR] No se pudo activar el venv. Revisa que Python este instalado.
  pause & exit /b 1
)

if exist "requirements.txt" (
  echo [PIP] Instalando dependencias desde requirements.txt...
  pip install -r requirements.txt
)

if exist ".env" (
  echo [PIP] Detecte .env -> instalando spotipy y python-dotenv...
  pip install spotipy python-dotenv
)

where nircmd.exe >nul 2>&1
if errorlevel 1 (
  if not exist "%COMP%\nircmd.exe" (
    echo [AVISO] nircmd.exe NO encontrado. Copialo a %COMP% o al PATH.
  ) else (
    echo [OK] nircmd.exe detectado en %COMP%.
  )
) else (
  echo [OK] nircmd.exe detectado en PATH.
)

echo.
echo [START] Abriendo ventanas (no se cerraran si hay error)...

REM Companion en ventana propia (queda abierta siempre)
start "StreamDeck Companion" cmd /k ^
 "cd /d %COMP% && call .venv\Scripts\activate && python companion.py & echo. & echo [Companion] Presione una tecla para cerrar esta ventana... & pause >nul"

REM Web server en ventana propia (queda abierta siempre)
start "StreamDeck Web" cmd /k ^
 "cd /d %WEB% && python -m http.server 8080 & echo. & echo [Web] Presione una tecla para cerrar esta ventana... & pause >nul"

timeout /t 2 >nul
start "" http://localhost:8080/client.html

echo.
echo [LISTO] Companion y Web levantados.
endlocal
exit /b 0
