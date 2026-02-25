import asyncio
import json
import websockets
from websockets.server import serve
from urllib.parse import urlparse, parse_qs

from ..config import PORT
from ..profiles.manager import profile_manager
from ..services.spotify import spotify_service
from ..services.telemetry import telemetry_service
from ..services.system import execute_cmd, open_url, set_volume, toggle_mute, SystemController

class CompanionServer:
    def __init__(self):
        self.clients = set()
        self.running = True

    async def register(self, ws):
        self.clients.add(ws)

    async def unregister(self, ws):
        self.clients.discard(ws)

    async def execute_action(self, action):
        atype = action.get("type")
        
        if atype == "spotify":
            return await asyncio.to_thread(spotify_service.execute, action)
        
        elif atype == "system":
            cmd = action.get("cmd")
            if cmd == "volume":
                set_volume(int(action.get("val", 50)))
            elif cmd == "volume_up":
                SystemController.change_volume_relative(5)
            elif cmd == "volume_down":
                SystemController.change_volume_relative(-5)
            elif cmd == "mute" or cmd == "mute_toggle":
                toggle_mute()
            elif cmd == "lock" or cmd == "lock_workstation" or cmd == "lock_pc":
                SystemController.lock_screen()
            elif cmd == "open_url":
                open_url(action.get("url"))
            elif cmd == "exec":
                execute_cmd(action.get("command"))
            
            print(f"[System] Action executed: {cmd}")
            return True
        
        return False

    async def handle_client(self, ws):
        # Parse Device ID
        query = parse_qs(urlparse(ws.path).query)
        device_id = query.get("device", ["unknown_device"])[0]
        
        print(f"[Server] Connected: {device_id}")
        await self.register(ws)

        # Send Initial Config
        try:
            pdata = profile_manager.load_profile(device_id)
            await ws.send(json.dumps({"type": "config", "data": pdata}))
            
            # Send initial Spotify state
            playing = spotify_service.get_now_playing()
            if playing:
                await ws.send(json.dumps(playing))
                
        except Exception as e:
            print(f"[Server] Error processing handshake {device_id}: {e}")

        # Message Loop
        try:
            async for msg in ws:
                # print(f"[Input] Raw: {msg}") # Too verbose?
                data = json.loads(msg)
                mtype = data.get("type")
                
                print(f"[Input] Type: {mtype} | Data: {str(data)[:100]}")

                if mtype == "exec":
                    ok = await self.execute_action(data.get("action", {}))
                    # Optional: Ack
                
                elif mtype == "save_layout":
                    profile_manager.save_layout_change(
                        device_id, 
                        data.get("pageId", "home"), 
                        data.get("layout", [])
                    )
                    
        except Exception as e:
            print(f"[Server] Error with {device_id}: {e}")
        finally:
            await self.unregister(ws)
            print(f"[Server] Disconnected: {device_id}")

    async def broadcast_loop(self):
        print("[Server] Starting Broadcast Loop (Spotify & Telemetry)")
        while self.running:
            if self.clients:
                # 1. Spotify
                if spotify_service.client:
                    info = spotify_service.get_now_playing()
                    if info:
                        await self._broadcast(json.dumps(info))
                
                # 2. Telemetry (Every 1s)
                stats = telemetry_service.get_stats()
                await self._broadcast(json.dumps(stats))

            await asyncio.sleep(1)

    async def _broadcast(self, message):
        for ws in list(self.clients):
            try:
                await ws.send(message)
            except:
                pass

    async def start(self):
        print(f"[Server] Listening on 0.0.0.0:{PORT}")
        
        # Start WebSocket Server
        async with serve(self.handle_client, "0.0.0.0", PORT):
            # Run broadcast loop concurrently
            await self.broadcast_loop()

# Singleton
server = CompanionServer()
