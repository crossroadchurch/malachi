import asyncio
import json
import time
import os, platform, pathlib
import websockets
import subprocess
from ThreadedHTTPServer import ThreadedHTTPServer
from Service import Service
from BiblePassage import BiblePassage, InvalidVersionError, InvalidVerseIdError, MalformedReferenceError
from Song import Song, InvalidSongIdError
from Presentation import Presentation, InvalidPresentationUrlError
from PresentationHandler import PresentationHandler

SOCKET_TYPES = ['singers', 'control', 'display', 'music']
SOCKETS = set()
CAPOS = dict()
MAIN_DISPLAYS = set()
screen_state = "on"

def register(websocket, path):
    # Use path to determine and store type of socket (e.g. display, musician, singer) in SOCKETS
    SOCKETS.add((websocket, path[1:]))
    CAPOS[websocket] = 0
    if path[1:] == "display":
        MAIN_DISPLAYS.add((websocket, path[1:]))

def unregister(websocket, path):
    # websocket has been closed by client
    SOCKETS.remove((websocket, path[1:]))
    if websocket in CAPOS:
        del CAPOS[websocket]
    if path[1:] == "display":
        MAIN_DISPLAYS.remove((websocket, path[1:]))

async def singers_init(websocket):
    await websocket.send(json.dumps({
        "action" : "update.service-overview-update", 
        "params" : json.loads(s.to_JSON_titles_and_current(CAPOS[websocket]))
        }))

async def control_init(websocket):
    await websocket.send(json.dumps({
        "action" : "update.service-overview-update", 
        "params" : json.loads(s.to_JSON_titles_and_current(CAPOS[websocket]))
        }))

async def display_init(websocket):
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
        "control": control_init,
        "music": singers_init
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
                "command.goto-slide": goto_slide,
                "command.next-item": next_item,
                "command.previous-item": previous_item,
                "command.goto-item": goto_item,
                "command.add-bible-item": add_bible_item,
                "command.add-song-item": add_song_item,
                "command.add-presentation": add_presentation,
                "command.remove-item": remove_item,
                "command.move-item": move_item,
                "command.set-display-state": set_display_state,
                "client.set-capo": set_capo,
                "query.bible-by-text": bible_text_query,
                "query.bible-by-ref": bible_ref_query,
                "query.song-by-text": song_text_query,
                "request.full-song": request_full_song,
                "request.bible-versions": request_bible_versions,
                "request.bible-books": request_bible_books,
                "request.chapter-structure": request_chapter_structure,
                "request.all-presentations": request_all_presentations
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
        if len(s.items) == 0:
            cur_item = {}
        else:
            cur_item = json.loads(s.items[s.item_index].to_JSON(CAPOS[socket[0]]))
        await socket[0].send(json.dumps({
            "action" : "update.item-index-update", 
            "params" : {
                "item_index": s.item_index, 
                "slide_index": s.slide_index,
                "current_item": cur_item
                }
            }))

async def clients_service_items_update():
    for socket in SOCKETS:
        # TODO: Do we need to send this to all clients?
        await socket[0].send(json.dumps({
            "action" : "update.service-overview-update", 
            "params" : json.loads(s.to_JSON_titles_and_current(CAPOS[socket[0]]))
            }))

# Command functions
async def next_slide(websocket, params):
    result = update_impress_next_effect()
    if result == -1:
        # We are not on a presentation, so advance slide as normal
        if s.next_slide():
            await clients_slide_index_update()
    else:
        # We are showing a presentation, so update service slide index based on result
        s.set_slide_index(result)
        await clients_slide_index_update()

async def previous_slide(websocket, params):
    result = update_impress_previous_effect()
    if result == -1:
        # We are not on a presentation, so advance slide as normal
        if s.previous_slide():
            await clients_slide_index_update()
    else:
        # We are showing a presentation, so update service slide index based on result
        s.set_slide_index(result)
        await clients_slide_index_update()

async def goto_slide(websocket, params):
    update_impress_goto_slide(int(params["index"]))
    if s.set_slide_index(int(params["index"])):
        await clients_slide_index_update()

async def next_item(websocket, params):
    if s.next_item():
        update_impress_change_item()
        await clients_item_index_update()

async def previous_item(websocket, params):
    if s.previous_item():
        update_impress_change_item()
        await clients_item_index_update()

async def goto_item(websocket, params):
    if s.set_item_index(int(params["index"])):
        update_impress_change_item()
        await clients_item_index_update()

async def remove_item(websocket, params):
    # TODO: What if this is the current item???
    s.remove_item_at(int(params["index"]))
    await clients_service_items_update()

async def move_item(websocket, params):
    # TODO: How does this affect the current item, particularly if it's a presentation?
    s.move_item(int(params["from-index"]), int(params["to-index"]))
    await clients_service_items_update()

async def add_bible_item(websocket, params):
    # TODO: Exception handling
    s.add_item(BiblePassage(params["version"], params["start-verse"], params["end-verse"]))
    await clients_service_items_update()

async def add_song_item(websocket, params):
    # TODO: Exception handling
    s.add_item(Song(params["song-id"]))
    await clients_service_items_update()

async def add_presentation(websocket, params):
    # TODO: Exception handling
    s.add_item(Presentation(params["url"]))
    await clients_service_items_update()

async def set_display_state(websocket, params):
    screen_state = params["state"]
    for socket in MAIN_DISPLAYS:
        await socket[0].send(json.dumps({
            "action" : "update.display-state", 
            "params" : {
                "state": screen_state
                }
            }))
    update_impress_screen_state()

# Client functions - response to client only
async def set_capo(websocket, params):
    CAPOS[websocket] = int(params["capo"])
    if len(s.items) == 0:
        cur_item = {}
    else:
        cur_item = json.loads(s.items[s.item_index].to_JSON(CAPOS[websocket]))
    await websocket.send(json.dumps({
        "action" : "update.item-index-update", 
        "params" : {
            "item_index": s.item_index, 
            "slide_index": s.slide_index,
            "current_item": cur_item
            }
        }))

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

async def song_text_query(websocket, params):
    result = Song.text_search(params["search-text"])
    await websocket.send(json.dumps({
        "action": "result.song-titles",
        "params": {
            "songs": json.loads(result)
        }}))

# Other requests
async def request_full_song(websocket, params):
    try:
        sg = Song(params["song-id"])
        await websocket.send(json.dumps({
            "action": "result.song-details",
            "params": {
                "status": "ok",
                "song-data": json.loads(sg.to_JSON_full_data())
            }
        }))
    except InvalidSongIdError:
        await websocket.send(json.dumps({
            "action": "result.song-details",
            "params": {
                "status": "invalid-id",
                "song-data": {}
            }
        }))

async def request_bible_versions(websocket, params):
    await websocket.send(json.dumps({
        "action": "result.bible-versions",
        "params": {
            "versions": BiblePassage.get_versions()
        }
    }))

async def request_bible_books(websocket, params):
    try:
        books = BiblePassage.get_books(params["version"])
        await websocket.send(json.dumps({
            "action": "result.bible-books",
            "params": {
                "status": "ok",
                "books": books
            }
        }))
    except InvalidVersionError:
        await websocket.send(json.dumps({
            "action": "result.bible-books",
            "params": {
                "status": "invalid-version",
                "books": []
            }
        }))

async def request_chapter_structure(websocket, params):
    try:
        chapters = BiblePassage.get_chapter_structure(params["version"])
        await websocket.send(json.dumps({
            "action": "result.chapter-structure",
            "params": {
                "status": "ok",
                "chapter-structure": chapters
            }
        }))
    except InvalidVersionError:
        await websocket.send(json.dumps({
            "action": "result.chapter-structure",
            "params": {
                "status": "invalid-version",
                "chapter-structure": []
            }
        }))

async def request_all_presentations(websocket, params):
    urls = Presentation.get_all_presentations()
    await websocket.send(json.dumps({
        "action": "result.all-presentations",
        "params": {
            "urls": urls
        }
    }))


# Presentation control with LibreOffice
def update_impress_change_item():
    # If previous item was a presentation then unload it
    if ph.pres_loaded == True:
        ph.unload_presentation()
    # If current item is a presentation then load it
    if s.get_current_item_type() == "Presentation":
        ph.load_presentation(pathlib.Path(os.path.abspath(s.items[s.item_index].url)).as_uri())
        # Show presentation if screen state allows it
        if screen_state == "on":
            ph.start_presentation()

def update_impress_screen_state():
    if s.get_current_item_type() == "Presentation":
        # Start or end presentation as necessary
        if screen_state == "on" and ph.pres_started == False:
            ph.start_presentation()
        elif screen_state == "off" and ph.pres_started == True:
            ph.stop_presentation()

def update_impress_goto_slide(index):
    if s.get_current_item_type() == "Presentation":
        if ph.pres_started == True:
            ph.load_effect(index)

def update_impress_next_effect():
    if s.get_current_item_type() == "Presentation":
        index = ph.next_effect()
        return index
    else:
        return -1

def update_impress_previous_effect():
    if s.get_current_item_type() == "Presentation":
        index = ph.previous_effect()
        return index
    else:
        return -1


if __name__ == "__main__":  
    # Start web server
    server = ThreadedHTTPServer('localhost', 8000)
    server.start()

    # Setup LibreOffice to receive UNO connections (for Linux)
    # Doesn't work.  Instead run soffice --accept="socket,host=localhost,port=2002;urp" --quickstart in a separate terminal before starting Malachi
    # subprocess.Popen(["soffice", "--accept='socket,host=localhost,port=2002;urp'", "--quickstart"])

    time.sleep(2)

    # Start presentation handler
    ph = PresentationHandler()

    # Load service
    s = Service()
    s.load_service('http://localhost:8000/service_test.json')
    s.set_item_index(0)

    # Start websocket server
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(responder, 'localhost', 9001)
    )
    asyncio.get_event_loop().run_forever()
    server.stop()