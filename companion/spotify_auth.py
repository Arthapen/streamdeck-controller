import os
from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI"),
    scope=os.getenv("SPOTIFY_SCOPES", "user-modify-playback-state user-read-playback-state"),
    cache_path=os.getenv("SPOTIFY_CACHE", ".cache-spotify"),
    open_browser=True
))

me = sp.me()
print("✅ Spotify autorizado para:", me["display_name"])
