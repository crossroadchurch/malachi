import asyncio, json, time, os, platform, pathlib
import websockets
from ThreadedHTTPServer import ThreadedHTTPServer
from Service import Service
from BiblePassage import BiblePassage
from Song import Song
from Presentation import Presentation
from PresentationHandler import PresentationHandler
from MalachiExceptions import InvalidVersionError, InvalidVerseIdError, MalformedReferenceError
from MalachiExceptions import InvalidPresentationUrlError, InvalidSongIdError
from MalachiExceptions import InvalidServiceUrlError, MalformedServiceFileError, UnspecifiedServiceUrl

class MalachiServer():

    def __init__(self):
        self.SOCKET_TYPES = ['singers', 'control', 'display', 'music']
        self.SOCKETS = set()
        self.CAPOS = dict()
        self.MAIN_DISPLAYS = set()
        self.screen_state = "on"
        self.s = Service()
        self.ph = PresentationHandler()

    def register(self, websocket, path):
        # Use path to determine and store type of socket (e.g. display, musician, singer) in SOCKETS
        self.SOCKETS.add((websocket, path[1:]))
        self.CAPOS[websocket] = 0
        if path[1:] == "display":
            self.MAIN_DISPLAYS.add((websocket, path[1:]))

    def unregister(self,websocket, path):
        # websocket has been closed by client
        self.SOCKETS.remove((websocket, path[1:]))
        if websocket in self.CAPOS:
            del self.CAPOS[websocket]
        if path[1:] == "display":
            self.MAIN_DISPLAYS.remove((websocket, path[1:]))

    async def singers_init(self, websocket):
        await websocket.send(json.dumps({
            "action" : "update.service-overview-update", 
            "params" : json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
            }))

    async def control_init(self, websocket):
        await websocket.send(json.dumps({
            "action" : "update.service-overview-update", 
            "params" : json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
            }))

    async def display_init(self, websocket):
        await websocket.send(json.dumps({
            "action" : "update.service-overview-update", 
            "params" : json.loads(self.s.to_JSON_simple())
            }))

    async def responder(self, websocket, path):
        # Websocket is opened by client
        self.register(websocket, path)

        # Send initial data packet based on path
        initial_data_switcher =  {
            "singers": self.singers_init,
            "control": self.control_init,
            "music": self.singers_init
        }
        if path[1:] in self.SOCKET_TYPES:
            initial_func = initial_data_switcher.get(path[1:], lambda: "None")
            await initial_func(websocket)

        try:
            # Websocket message loop
            async for message in websocket:
                json_data = json.loads(message)
                command_switcher = {
                    "command.next-slide": self.next_slide,
                    "command.previous-slide": self.previous_slide,
                    "command.goto-slide": self.goto_slide,
                    "command.next-item": self.next_item,
                    "command.previous-item": self.previous_item,
                    "command.goto-item": self.goto_item,
                    "command.add-bible-item": self.add_bible_item,
                    "command.add-song-item": self.add_song_item,
                    "command.add-presentation": self.add_presentation,
                    "command.remove-item": self.remove_item,
                    "command.move-item": self.move_item,
                    "command.set-display-state": self.set_display_state,
                    "command.new-service": self.new_service,
                    "command.load-service": self.load_service,
                    "command.save-service": self.save_service,
                    "command.save-service-as": self.save_service_as,
                    "client.set-capo": self.set_capo,
                    "query.bible-by-text": self.bible_text_query,
                    "query.bible-by-ref": self.bible_ref_query,
                    "query.song-by-text": self.song_text_query,
                    "request.full-song": self.request_full_song,
                    "request.bible-versions": self.request_bible_versions,
                    "request.bible-books": self.request_bible_books,
                    "request.chapter-structure": self.request_chapter_structure,
                    "request.all-presentations": self.request_all_presentations,
                    "request.all-services": self.request_all_services
                }
                command_handler = command_switcher.get(json_data["action"], lambda: "None")
                await command_handler(websocket, json_data["params"])
        finally:
            # Websocket is closed by client
            self.unregister(websocket, path)

    # Update functions
    async def clients_slide_index_update(self):
        for socket in self.SOCKETS:
            # TODO: Do we need to send this to all clients?
            # TODO: Do we need to allow the client to check that they have the current version of the service e.g. through MD5 sum?
            await socket[0].send(json.dumps({
                "action" : "update.slide-index-update", 
                "params" : {
                    "item_index": self.s.item_index, 
                    "slide_index": self.s.slide_index
                    }
                }))

    async def clients_item_index_update(self):
        for socket in self.SOCKETS:
            # TODO: Do we need to send this to all clients?
            # TODO: Do we need to allow the client to check that they have the current version of the service e.g. through MD5 sum?
            if len(self.s.items) == 0:
                cur_item = {}
            else:
                cur_item = json.loads(self.s.items[s.item_index].to_JSON(self.CAPOS[socket[0]]))
            await socket[0].send(json.dumps({
                "action" : "update.item-index-update", 
                "params" : {
                    "item_index": self.s.item_index, 
                    "slide_index": self.s.slide_index,
                    "current_item": cur_item
                    }
                }))

    async def clients_service_items_update(self):
        for socket in self.SOCKETS:
            # TODO: Do we need to send this to all clients?
            await socket[0].send(json.dumps({
                "action" : "update.service-overview-update", 
                "params" : json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[socket[0]]))
                }))

    # Command functions
    async def next_slide(self, websocket, params):
        result = self.update_impress_next_effect()
        if result == -1:
            # We are not on a presentation, so advance slide as normal
            if self.s.next_slide():
                await self.clients_slide_index_update()
        else:
            # We are showing a presentation, so update service slide index based on result
            self.s.set_slide_index(result)
            await self.clients_slide_index_update()

    async def previous_slide(self, websocket, params):
        result = self.update_impress_previous_effect()
        if result == -1:
            # We are not on a presentation, so advance slide as normal
            if self.s.previous_slide():
                await self.clients_slide_index_update()
        else:
            # We are showing a presentation, so update service slide index based on result
            self.s.set_slide_index(result)
            await self.clients_slide_index_update()

    async def goto_slide(self, websocket, params):
        self.update_impress_goto_slide(int(params["index"]))
        if self.s.set_slide_index(int(params["index"])):
            await self.clients_slide_index_update()

    async def next_item(self, websocket, params):
        if self.s.next_item():
            self.update_impress_change_item()
            await self.clients_item_index_update()

    async def previous_item(self, websocket, params):
        if self.s.previous_item():
            self.update_impress_change_item()
            await self.clients_item_index_update()

    async def goto_item(self, websocket, params):
        if self.s.set_item_index(int(params["index"])):
            self.update_impress_change_item()
            await self.clients_item_index_update()

    async def remove_item(self, websocket, params):
        # TODO: Exception: What if this is the current item??
        self.s.remove_item_at(int(params["index"]))
        await self.clients_service_items_update()

    async def move_item(self, websocket, params):
        # TODO: How does this affect the current item, particularly if it's a presentation?
        self.s.move_item(int(params["from-index"]), int(params["to-index"]))
        await self.clients_service_items_update()

    async def add_bible_item(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.add_item(BiblePassage(params["version"], params["start-verse"], params["end-verse"]))
        except InvalidVersionError as e:
            status, details = "invalid-version", e.msg
        except InvalidVerseIdError as e:
            status, details = "invalid-verse", e.msg
        finally:
            await websocket.send(json.dumps({
                "action" : "response.add-bible-item", 
                "params" : {
                    "status": status, 
                    "details": details
                    }
                }))
            await self.clients_service_items_update()

    async def add_song_item(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.add_item(Song(params["song-id"]))
        except InvalidSongIdError as e:
            status, details = "invalid-song", e.msg
        finally:
            await websocket.send(json.dumps({
                "action" : "response.add-song-item", 
                "params" : {
                    "status": status, 
                    "details": details
                    }
                }))
            await self.clients_service_items_update()

    async def add_presentation(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.add_item(Presentation(params["url"]))
        except InvalidPresentationUrlError as e:
            status, details = "invalid-presentation", e.msg
        finally:
            await websocket.send(json.dumps({
                "action" : "response.add-presentation", 
                "params" : {
                    "status": status, 
                    "details": details
                    }
                }))
            await self.clients_service_items_update()

    async def set_display_state(self, websocket, params):
        self.screen_state = params["state"]
        for socket in self.MAIN_DISPLAYS:
            await socket[0].send(json.dumps({
                "action" : "update.display-state", 
                "params" : {
                    "state": self.screen_state
                    }
                }))
        self.update_impress_screen_state()

    async def new_service(self, websocket, params):
        self.s = Service()
        await self.clients_service_items_update()

    async def load_service(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.load_service(params["filename"])
        except InvalidServiceUrlError as e:
            self.s = Service()
            status, details = "invalid-url", e.msg
        except MalformedServiceFileError as e:
            self.s = Service()
            status, details = "malformed-json", e.msg
        finally:
            await websocket.send(json.dumps({
                "action" : "response.load-service", 
                "params" : {
                    "status": status,
                    "details": details
                    }
                }))
            await self.clients_service_items_update()
        
    async def save_service(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.save()
        except UnspecifiedServiceUrl as e:
            status, details = "unspecified-service", e.msg
        finally:
            await websocket.send(json.dumps({
                "action" : "response.save-service", 
                "params" : {
                    "status": status,
                    "details": details
                    }
                }))

    async def save_service_as(self, websocket, params):
        self.s.save_as(params["filename"])
        await websocket.send(json.dumps({
            "action" : "response.save-service", 
            "params" : {
                "status": "ok",
                "details": ""
                }
            }))

    # Client functions - response to client only
    async def set_capo(self, websocket, params):
        self.CAPOS[websocket] = int(params["capo"])
        if len(self.s.items) == 0:
            cur_item = {}
        else:
            cur_item = json.loads(self.s.items[s.item_index].to_JSON(self.CAPOS[websocket]))
        await websocket.send(json.dumps({
            "action" : "update.item-index-update", 
            "params" : {
                "item_index": self.s.item_index, 
                "slide_index": self.s.slide_index,
                "current_item": cur_item
                }
            }))

    # Query functions - response to client only
    async def bible_text_query(self, websocket, params):
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

    async def bible_ref_query(self, websocket, params):
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

    async def song_text_query(self, websocket, params):
        result = Song.text_search(params["search-text"])
        await websocket.send(json.dumps({
            "action": "result.song-titles",
            "params": {
                "songs": json.loads(result)
            }}))

    # Other requests
    async def request_full_song(self, websocket, params):
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

    async def request_bible_versions(self, websocket, params):
        await websocket.send(json.dumps({
            "action": "result.bible-versions",
            "params": {
                "versions": BiblePassage.get_versions()
            }
        }))

    async def request_bible_books(self, websocket, params):
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

    async def request_chapter_structure(self, websocket, params):
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

    async def request_all_presentations(self, websocket, params):
        urls = Presentation.get_all_presentations()
        await websocket.send(json.dumps({
            "action": "result.all-presentations",
            "params": {
                "urls": urls
            }
        }))

    async def request_all_services(self, websocket, params):
        fnames = Service.get_all_services()
        await websocket.send(json.dumps({
            "action": "result.all-services",
            "params": {
                "filenames": fnames
            }
        }))


    # Presentation control with LibreOffice
    def update_impress_change_item(self):
        # If previous item was a presentation then unload it
        if self.ph.pres_loaded == True:
            self.ph.unload_presentation()
        # If current item is a presentation then load it
        if self.s.get_current_item_type() == "Presentation":
            self.ph.load_presentation(pathlib.Path(os.path.abspath(self.s.items[self.s.item_index].url)).as_uri())
            # Show presentation if screen state allows it
            if self.screen_state == "on":
                self.ph.start_presentation()

    def update_impress_screen_state(self):
        if self.s.get_current_item_type() == "Presentation":
            # Start or end presentation as necessary
            if self.screen_state == "on" and self.ph.pres_started == False:
                self.ph.start_presentation()
            elif self.screen_state == "off" and self.ph.pres_started == True:
                self.ph.stop_presentation()

    def update_impress_goto_slide(self, index):
        if self.s.get_current_item_type() == "Presentation":
            if self.ph.pres_started == True:
                self.ph.load_effect(index)

    def update_impress_next_effect(self):
        if self.s.get_current_item_type() == "Presentation":
            index = self.ph.next_effect()
            return index
        else:
            return -1

    def update_impress_previous_effect(self):
        if self.s.get_current_item_type() == "Presentation":
            index = self.ph.previous_effect()
            return index
        else:
            return -1


if __name__ == "__main__":  
    # Start web server
    server = ThreadedHTTPServer('localhost', 8000)
    server.start()

    # In Linux need to run soffice --accept="socket,host=localhost,port=2002;urp" --quickstart in a separate terminal before starting Malachi

    time.sleep(2)

    m = MalachiServer()
    m.s.load_service('service_test.json')
    m.s.set_item_index(0)

    # Start websocket server
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(m.responder, 'localhost', 9001)
    )
    asyncio.get_event_loop().run_forever()
    server.stop()