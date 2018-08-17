import asyncio
import json
import time
import websockets
from ThreadedHTTPServer import ThreadedHTTPServer
from Service import Service
from BiblePassage import BiblePassage, InvalidVersionError, InvalidVerseIdError, MalformedReferenceError

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
        "action" : "update.service-overview-update", 
        "params" : json.loads(s.to_JSON_simple())
        }))

async def control_init(websocket):
    await websocket.send(json.dumps({
        "action" : "update.service-overview-update", 
        "params" : json.loads(s.to_JSON_simple())
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
            command_switcher = {
                "command.next-slide": next_slide,
                "command.previous-slide": previous_slide,
                "command.next-item": next_item,
                "command.previous-item": previous_item,
                "command.add-bible-item": add_bible_item,
                "command.remove-item": remove_item,
                "command.move-item": move_item,
                "query.bible-by-text": bible_text_query,
                "query.bible-by-ref": bible_ref_query
            }
            command_handler = command_switcher.get(json_data["action"], lambda: "None")
            await command_handler(websocket, json_data["params"])
    finally:
        # Websocket is closed by client
        unregister(websocket, path)

# Update functions
async def clients_slide_index_update():
    for socket in SOCKETS:
        # TODO: Do we need to send this to all clients?
        # TODO: Do we need to allow the client to check that they have the current version of the service e.g. through MD5 sum?
        await socket[0].send(json.dumps({
            "action" : "update.slide-index-update", 
            "params" : {
                "item_index": s.item_index, 
                "slide_index": s.slide_index
                }
            }))

async def clients_item_index_update():
    for socket in SOCKETS:
        # TODO: Do we need to send this to all clients?
        # TODO: Do we need to allow the client to check that they have the current version of the service e.g. through MD5 sum?
        await socket[0].send(json.dumps({
            "action" : "update.item-index-update", 
            "params" : {
                "item_index": s.item_index, 
                "slide_index": s.slide_index,
                "item_slides": s.items[s.item_index].slides
                }
            }))

async def clients_service_items_update():
    for socket in SOCKETS:
        # TODO: Do we need to send this to all clients?
        await socket[0].send(json.dumps({
            "action" : "update.service-overview-update", 
            "params" : json.loads(s.to_JSON_simple())
            }))

# Command functions
async def next_slide(websocket, params):
    s.next_slide()
    await clients_slide_index_update()

async def previous_slide(websocket, params):
    s.previous_slide()
    await clients_slide_index_update()

async def next_item(websocket, params):
    s.next_item()
    await clients_item_index_update()

async def previous_item(websocket, params):
    s.previous_item()
    await clients_item_index_update()

async def remove_item(websocket, params):
    s.remove_item_at(int(params["index"]))
    await clients_service_items_update()

async def move_item(websocket, params):
    s.move_item(int(params["from-index"]), int(params["to-index"]))
    await clients_service_items_update()

async def add_bible_item(websocket, params):
    s.add_item(BiblePassage(params["version"], params["start-verse"], params["end-verse"]))
    await clients_service_items_update()

# Query functions - response to client only
async def bible_text_query(websocket, params):
    try:
        result = BiblePassage.text_search(params["version"], params["search-text"])
        await websocket.send(json.dumps({
            "action": "result.bible-verses",
            "params": {
                "status": "ok",
                "verses": json.loads(result)
            }}))
    except InvalidVersionError:
        await websocket.send(json.dumps({
            "action": "result.bible-verses",
            "params": {
                "status": "invalid-version",
                "verses": []
            }}))
    except (InvalidReferenceError, MalformedReferenceError):
        await websocket.send(json.dumps({
            "action": "result.bible-verses",
            "params": {
                "status": "invalid-version",
                "verses": []
            }}))

async def bible_ref_query(websocket, params):
    try:
        result = BiblePassage.ref_search(params["version"], params["search-ref"])
        await websocket.send(json.dumps({
            "action": "result.bible-verses",
            "params": {
                "status": "ok",
                "verses": json.loads(result)
            }}))
    except InvalidVersionError:
        await websocket.send(json.dumps({
            "action": "result.bible-verses",
            "params": {
                "status": "invalid-version",
                "verses": []
            }}))
    except (InvalidReferenceError, MalformedReferenceError):
        await websocket.send(json.dumps({
            "action": "result.bible-verses",
            "params": {
                "status": "invalid-version",
                "verses": []
            }}))

if __name__ == "__main__":  
    # Start web server
    server = ThreadedHTTPServer('localhost', 8000)
    server.start()

    time.sleep(2)
    
    s = Service()
    s.load_service('http://localhost:8000/service_test.json')
    s.save_to_JSON()

    # Start websocket server
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(responder, 'localhost', 9001)
    )
    asyncio.get_event_loop().run_forever()
    server.stop()