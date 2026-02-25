import asyncio
from lib.core.server import server

if __name__ == "__main__":
    print("--- StreamDeck Controller V2 Backend ---")
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("Stopped by user.")
