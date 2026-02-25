@echo off
cd /d D:\Programacion\StreamDeck\companion
if not exist .venv (
  py -3 -m venv .venv
)
call .venv\Scripts\activate
pip install -r requirements.txt
echo.
echo Iniciando Companion WebSocket...
py companion.py
echo.
echo (Si hubo un error arriba, quedo pausado para que lo veas)
pause
