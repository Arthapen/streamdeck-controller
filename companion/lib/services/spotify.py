import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ..config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, BASE_DIR

class SpotifyService:
    def __init__(self):
        self.client = None
        self.connect()

    def connect(self):
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            print("[Spotify] Credentials missing in .env")
            return

        cache_path = os.path.join(BASE_DIR, ".cache-spotify")

        try:
            self.client = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET,
                redirect_uri=SPOTIFY_REDIRECT_URI,
                scope="user-read-playback-state user-modify-playback-state",
                open_browser=False,
                cache_path=cache_path
            ))
            print("[Spotify] Service Initialized")
        except Exception as e:
            print(f"[Spotify] Init Error: {e}")

    def get_now_playing(self):
        if not self.client: return None
        try:
            current = self.client.current_playback()
            if current and current['item']:
                track = current['item']
                
                track_id = track['id']
                is_liked = False
                try:
                    is_liked = self.client.current_user_saved_tracks_contains([track_id])[0]
                except:
                    pass

                return {
                    "type": "now_playing",
                    "id": track['id'],
                    "title": track['name'],
                    "artist": ", ".join([a['name'] for a in track['artists']]),
                    "image": track['album']['images'][0]['url'] if track['album']['images'] else "",
                    "is_playing": current['is_playing'],
                    "progress_ms": current['progress_ms'],
                    "duration_ms": track['duration_ms'],
                    "is_liked": is_liked
                }
        except Exception as e:
            # Token expired or network error
            print(f"[Spotify] Error polling: {e}")
        return None

    def execute(self, action):
        if not self.client: return False
        try:
            cmd = action.get('cmd')
            print(f"[Spotify] Executing Command: {cmd} | Params: {action}")
            if cmd == "play": self.client.start_playback()
            elif cmd == "pause": self.client.pause_playback()
            elif cmd == "toggle_play":
                cur = self.client.current_playback()
                if cur and cur['is_playing']: self.client.pause_playback()
                else: self.client.start_playback()
            elif cmd == "next": self.client.next_track()
            elif cmd == "prev": self.client.previous_track()
            elif cmd == "seek":
                pos = int(action.get('value', 0))
                self.client.seek_track(pos)
            elif cmd == "like":
                tid = action.get('track_id')
                if tid: self.client.current_user_saved_tracks_add([tid])
            elif cmd == "dislike":
                # For dislike we will just skip, but if we wanted to remove from library:
                # tid = action.get('track_id')
                # if tid: self.client.current_user_saved_tracks_delete([tid])
                self.client.next_track() # Skip is the most common behavior for "dislike" in radios
            
            return True
        except Exception as e:
            print(f"[Spotify] Cmd Error ({action}): {e}")
            return False
            
# Singleton instance
spotify_service = SpotifyService()
