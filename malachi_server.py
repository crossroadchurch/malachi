import asyncio
import json
import websockets
from ThreadedHTTPServer import ThreadedHTTPServer

SOCKETS = set()

def register(websocket, path):
    # Use path to determine and store type of socket (e.g. display, musician, singer) in SOCKETS
    SOCKETS.add((websocket, path))
    print(SOCKETS)

def unregister(websocket, path):
    SOCKETS.remove((websocket, path))
    print(SOCKETS)

async def responder(websocket, path):
    register(websocket, path)
    try:
        async for message in websocket:
            data = json.loads(message)
    finally:
        unregister(websocket, path)

server = ThreadedHTTPServer('localhost', 8000)
server.start()

asyncio.get_event_loop().run_until_complete(
    websockets.serve(responder, 'localhost', 9001)
)
asyncio.get_event_loop().run_forever()
server.stop()