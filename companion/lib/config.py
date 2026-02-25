import os
import sys
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Constants
PORT = 8765
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # companion/
NIRCMD_PATH = os.path.join(BASE_DIR, "nircmd.exe")
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")

# Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
