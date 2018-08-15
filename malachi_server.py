import asyncio
import json
import websockets
from ThreadedHTTPServer import ThreadedHTTPServer
from Service import Service
from BiblePassage import BiblePassage
from BibleReference import BibleReference

SOCKET_TYPES = ['singers', 'control']
SOCKETS = set()

def register(websocket, path):
    # Use path to determine and store type of socket (e.g. display, musician, singer) in SOCKETS
    SOCKETS.add((websocket, path[1:]))

def unregister(websocket, path):
    # websocket has been closed by client
    SOCKETS.remove((websocket, path[1:]))

async def singers_init(websocket):
    await websocket.send(json.dumps({
        "type" : "update", 
        "subtype" : "service-overview-update", 
        "data" : json.loads(s.to_JSON_simple())
        }))

async def control_init(websocket):
    await websocket.send(json.dumps({
        "type" : "update", 
        "subtype" : "service-overview-update", 
        "data" : json.loads(s.to_JSON_simple())
        }))

async def responder(websocket, path):
    # Websocket is opened by client
    register(websocket, path)

    # Send initial data packet based on path
    initial_data_switcher =  {
        "singers": singers_init,
        "control": control_init
    }
    if path[1:] in SOCKET_TYPES:
        initial_func = initial_data_switcher.get(path[1:], lambda: "None")
        await initial_func(websocket)

    try:
        # Websocket message loop
        async for message in websocket:
            json_data = json.loads(message)
            print(json_data)
            if json_data["type"] == "command":
                command_switcher = {
                    "next-slide": next_slide,
                    "previous-slide": previous_slide,
                    "next-item": next_item,
                    "previous-item": previous_item
                }
                command_handler = command_switcher.get(json_data["subtype"], lambda: "None")
                await command_handler(websocket, json_data["data"])
    finally:
        # Websocket is closed by client
        unregister(websocket, path)

# Update functions
async def clients_slide_index_update():
    for socket in SOCKETS:
        # TODO: Do we need to send this to all clients?
        # TODO: Do we need to allow the client to check that they have the current version of the service e.g. through MD5 sum?
        await socket[0].send(json.dumps({
            "type" : "update", 
            "subtype" : "slide-index-update", 
            "data" : {
                "item_index": s.item_index, 
                "slide_index": s.slide_index
                }
            }))

async def clients_item_index_update():
    for socket in SOCKETS:
        # TODO: Do we need to send this to all clients?
        # TODO: Do we need to allow the client to check that they have the current version of the service e.g. through MD5 sum?
        await socket[0].send(json.dumps({
            "type" : "update", 
            "subtype" : "item-index-update", 
            "data" : {
                "item_index": s.item_index, 
                "slide_index": s.slide_index,
                "item_slides": s.items[s.item_index].slides
                }
            }))

# Command functions
async def next_slide(websocket, data):
    s.next_slide()
    await clients_slide_index_update()

async def previous_slide(websocket, data):
    s.previous_slide()
    await clients_slide_index_update()

async def next_item(websocket, data):
    s.next_item()
    await clients_item_index_update()

async def previous_item(websocket, data):
    s.previous_item()
    await clients_item_index_update()


if __name__ == "__main__":
    s = Service()
    s.add_item(BiblePassage('NIV', BibleReference(13,1,8), BibleReference(13,1,10)))
    s.add_item(BiblePassage('NIV', BibleReference(13,2,8), BibleReference(13,2,10)))
    s.add_item(BiblePassage('NIV', BibleReference(13,3,8), BibleReference(13,3,10)))
    s.add_item(BiblePassage('NIV', BibleReference(13,4,8), BibleReference(13,4,10)))

    # Start web server
    server = ThreadedHTTPServer('localhost', 8000)
    server.start()

    # Start websocket server
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(responder, 'localhost', 9001)
    )
    asyncio.get_event_loop().run_forever()
    server.stop()