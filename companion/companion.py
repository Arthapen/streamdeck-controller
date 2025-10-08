import asyncio, json, subprocess, sys, os
from pathlib import Path

import websockets
from websockets.server import serve
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from keyboard import send as kb_send

# Spotify
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

# ----- Config -----
COMPANION_DIR = Path(__file__).resolve().parent
BASE_DIR = COMPANION_DIR.parent
PROFILES_PATH = COMPANION_DIR / "profiles.json"

HOST = "0.0.0.0"
PORT = 8765
TOKEN = "1234"

SPOTIFY: Spotify | None = None
CLIENTS = set()   # lista de clientes conectados
LAST_TRACK_ID = None

# ----- Utils -----
def log(*args):
    print("[companion]", *args, flush=True)

def run_nircmd(*args) -> bool:
    try:
        subprocess.run(["nircmd.exe", *args], check=True)
        return True
    except Exception as e:
        log("NirCmd error:", e)
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

# ----- Spotify -----
def init_spotify() -> Spotify:
    load_dotenv(dotenv_path=COMPANION_DIR / ".env")
    auth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
        scope=os.getenv("SPOTIFY_SCOPES", "user-modify-playback-state user-read-playback-state"),
        cache_path=os.getenv("SPOTIFY_CACHE", ".cache-spotify")
    )
    return Spotify(auth_manager=auth)

def get_now_playing(sp: Spotify) -> dict | None:
    try:
        track = sp.current_playback()
        if track and track.get("item"):
            item = track["item"]
            progress = int(track.get("progress_ms", 0) / 1000)  # segundos actuales
            duration = int(item.get("duration_ms", 0) / 1000)  # segundos totales
            return {
                "type": "now_playing",
                "track_id": item.get("id"),
                "title": item.get("name"),
                "artist": ", ".join(a["name"] for a in item.get("artists", [])),
                "album": item["album"]["name"] if item.get("album") else "",
                "image": item["album"]["images"][0]["url"] if item.get("album", {}).get("images") else "",
                "progress": progress,
                "duration": duration
            }
        return None
    except Exception as e:
        log("Error get_now_playing:", e)
        return None

async def broadcast_now_playing():
    """Loop que chequea cambios de canción y los manda a todos los clientes"""
    global LAST_TRACK_ID
    while True:
        await asyncio.sleep(3)  # cada 3 segundos
        if SPOTIFY is None: 
            continue
        info = get_now_playing(SPOTIFY)
        if info and info.get("track_id") != LAST_TRACK_ID:
            LAST_TRACK_ID = info.get("track_id")
            msg = json.dumps(info)
            log("Nuevo track:", info.get("title"), "-", info.get("artist"))
            for ws in list(CLIENTS):
                try:
                    await ws.send(msg)
                except:
                    CLIENTS.discard(ws)

# ----- Acciones -----
def execute_action(a: dict) -> bool:
    t = a.get("type")
    log("Acción recibida:", a)

    if t == "spotify":
        if SPOTIFY is None:
            return False
        cmd = a.get("cmd")
        try:
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
                return False
        except Exception as e:
            log("Error Spotify:", e)
            return False

    elif t == "system":
        cmd = a.get("cmd")
        if cmd == "volume_up":
            return run_nircmd("changesysvolume", "5000")
        elif cmd == "volume_down":
            return run_nircmd("changesysvolume", "-5000")
        elif cmd == "mute_toggle":
            return run_nircmd("mutesysvolume", "2")
        else:
            return False

    return False

# ----- WS -----
async def handle(ws):
    # auth
    q = {}
    raw_path = getattr(ws, "path", "") or ""
    if "?" in raw_path:
        for p in raw_path.split("?", 1)[1].split("&"):
            if "=" in p:
                k, v = p.split("=", 1)
                q[k] = v

    if q.get("token") != TOKEN:
        await ws.close(code=1008, reason="auth failed")
        return

    log("Cliente conectado.")
    CLIENTS.add(ws)

    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
                if data.get("type") == "exec":
                    ok = execute_action(data.get("action", {}))
                    await ws.send(json.dumps({"type":"ack","ok":ok}))
            except Exception as e:
                await ws.send(json.dumps({"type":"ack","ok":False,"err":str(e)}))
    except (ConnectionClosedOK, ConnectionClosedError):
        pass
    finally:
        CLIENTS.discard(ws)
        log("Cliente desconectado.")

# ----- Main -----
async def main():
    os.chdir(COMPANION_DIR)
    log(f"Carpeta actual: {os.getcwd()}")
    load_profiles()

    global SPOTIFY
    try:
        SPOTIFY = init_spotify()
        log("Spotify listo.")
    except Exception as e:
        log("Spotify no se inicializó:", e)

    log(f"WS en ws://0.0.0.0:{PORT}/?token={TOKEN}")
    async with serve(handle, HOST, PORT):
        await asyncio.gather(
            broadcast_now_playing(),  # loop de actualización automática
            asyncio.Future()          # mantener vivo el server
        )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
