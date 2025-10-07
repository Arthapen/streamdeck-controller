import asyncio, json, subprocess, sys, os
from pathlib import Path

import websockets
from websockets.server import serve
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from keyboard import send as kb_send

# Spotify
import os
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

# ----- Config -----
BASE_DIR = Path(r"D:\Programacion\StreamDeck")
COMPANION_DIR = BASE_DIR / "companion"
PROFILES_PATH = COMPANION_DIR / "profiles.json"

HOST = "0.0.0.0"
PORT = 8765
TOKEN = "1234"   # cámbialo si querés

SPOTIFY: Spotify | None = None

# ----- Utils -----
def log(*args):
    print("[companion]", *args, flush=True)

def run_nircmd(*args) -> bool:
    try:
        subprocess.run(["nircmd.exe", *args], check=True)
        return True
    except FileNotFoundError:
        log("NirCmd no encontrado. ¿Está nircmd.exe junto a companion.py o en PATH?")
        return False
    except subprocess.CalledProcessError as e:
        log("NirCmd devolvió error:", e)
        return False
    except Exception as e:
        log("NirCmd excepción:", e)
        return False

def load_profiles():
    if PROFILES_PATH.exists():
        try:
            with open(PROFILES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            names = [p.get("name") or p.get("id") for p in data.get("profiles", [])]
            log(f"[profiles.json] Perfiles: {names}")
        except Exception as e:
            log(f"[profiles.json] Error al cargar: {e}")
    else:
        log(f"[profiles.json] No existe -> {PROFILES_PATH}")

# ----- Spotify helpers -----
def init_spotify() -> Spotify:
    load_dotenv(dotenv_path=COMPANION_DIR / ".env")
    auth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=os.getenv("SPOTIFY_SCOPES", "user-modify-playback-state user-read-playback-state"),
        cache_path=os.getenv("SPOTIFY_CACHE", ".cache-spotify")
    )
    sp = Spotify(auth_manager=auth)
    return sp

def ensure_active_device(sp: Spotify) -> bool:
    """
    Garantiza que haya algún dispositivo activo.
    Si no lo hay, intenta transferir la reproducción al primer device disponible.
    Devuelve True si hay/queda activo; False si no.
    """
    try:
        devices = sp.devices() or {}
        devs = devices.get("devices", [])
        if not devs:
            log("Spotify: no hay dispositivos disponibles. Abrí Spotify en tu PC/celu y dale play una vez.")
            return False
        for d in devs:
            if d.get("is_active"):
                return True
        first = devs[0]
        did = first.get("id")
        if did:
            sp.transfer_playback(device_id=did, force_play=False)
            log(f"Spotify: transferida sesión al dispositivo '{first.get('name')}'.")
            return True
        return False
    except Exception as e:
        log("Spotify ensure_active_device error:", e)
        return False

# ----- Acciones -----
def execute_action(a: dict) -> bool:
    t = a.get("type")
    log("Acción recibida:", a)

    if t == "spotify":
        if SPOTIFY is None:
            log("Spotify no inicializado o sin tokens (.env/.cache-spotify).")
            return False
        cmd = a.get("cmd")
        try:
            if not ensure_active_device(SPOTIFY):
                return False
            if cmd == "toggle_play":
                pb = SPOTIFY.current_playback()
                if pb and pb.get("is_playing"):
                    SPOTIFY.pause_playback()
                else:
                    SPOTIFY.start_playback()
                return True
            elif cmd == "next":
                SPOTIFY.next_track()
                return True
            elif cmd == "prev":
                SPOTIFY.previous_track()
                return True
            else:
                log("Spotify cmd desconocido:", cmd)
                return False
        except Exception as e:
            log("Error Spotify:", e)
            return False

    if t == "media":
        cmd = a.get("cmd")
        mapping = {
            "toggle_play": ["sendkeypress", "mediaplaypause"],
            "next":        ["sendkeypress", "medianext"],
            "prev":        ["sendkeypress", "mediaprevious"],
        }
        args = mapping.get(cmd)
        if not args:
            log("Media cmd desconocido:", cmd)
            return False
        return run_nircmd(*args)

    elif t == "system":
        cmd = a.get("cmd")
        if cmd == "volume_up":
            return run_nircmd("changesysvolume", "5000")
        elif cmd == "volume_down":
            return run_nircmd("changesysvolume", "-5000")
        elif cmd == "mute_toggle":
            return run_nircmd("mutesysvolume", "2")
        else:
            log("System cmd desconocido:", cmd)
            return False

    elif t == "hotkey":
        keys = a.get("keys", "")
        try:
            kb_send(keys)   # ^+m = Ctrl+Shift+M ; #l = Win+L
            return True
        except Exception as e:
            log("Error enviando hotkey con keyboard:", e)
            return False

    elif t == "macro":
        steps = a.get("steps", [])
        try:
            for s in steps:
                st = s.get("type")
                if st == "keys":
                    kb_send(s.get("send", ""))
                elif st == "enter":
                    kb_send("{ENTER}")
                elif st == "sleep":
                    import time; time.sleep(float(s.get("sec", 0.1)))
                else:
                    log("Paso de macro desconocido:", st)
            return True
        except Exception as e:
            log("Error ejecutando macro:", e)
            return False

    elif t == "ping":
        # Heartbeat desde el cliente
        return True

    else:
        log("Tipo de acción desconocido:", t)
        return False

# ----- WS -----
async def handle(ws):
    # auth query
    q = {}
    try:
        raw_path = getattr(ws, "path", "") or ""
        if "?" in raw_path:
            qstring = raw_path.split("?", 1)[1]
            for p in qstring.split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    q[k] = v
    except Exception:
        pass

    if q.get("token") != TOKEN:
        await ws.close(code=1008, reason="auth failed")
        return

    log("Cliente conectado.")
    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
                if data.get("type") != "exec":
                    await ws.send(json.dumps({"type":"ack","ok":False,"err":"bad_type"}))
                    continue
                ok = execute_action(data.get("action", {}))
                await ws.send(json.dumps({"type":"ack","ok":ok}))
            except Exception as e:
                await ws.send(json.dumps({"type":"ack","ok":False,"err":str(e)}))
    except (ConnectionClosedOK, ConnectionClosedError) as e:
        log("Cliente desconectado:", repr(e))
    except Exception as e:
        log("Handler error (no crítico):", repr(e))
    finally:
        log("Conexión finalizada.")

async def main():
    os.chdir(COMPANION_DIR)  # asegurar cwd
    log(f"Carpeta actual: {os.getcwd()}")
    load_profiles()

    global SPOTIFY
    try:
        SPOTIFY = init_spotify()
        log("Spotify listo.")
    except Exception as e:
        log("Spotify no se inicializó:", e)

    log(f"WS en ws://0.0.0.0:{PORT}/?token={TOKEN}")
    async with serve(
        handle, HOST, PORT,
        ping_interval=20, ping_timeout=20,
        close_timeout=3, max_queue=None
    ):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print("CRASH EN ARRANQUE:", e)
        input("Presione ENTER para cerrar...")
