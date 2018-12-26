import json, os, platform, pathlib, threading
import websockets
from json.decoder import JSONDecodeError
from .ThreadedHTTPServer import ThreadedHTTPServer
from .Service import Service
from .BiblePassage import BiblePassage
from .Song import Song
from .Presentation import Presentation
from .PresentationHandler import PresentationHandler
from .LightHandler import LightHandler
from .Video import Video
from .Tracker import Tracker
from .MalachiExceptions import InvalidVersionError, InvalidVerseIdError, MalformedReferenceError
from .MalachiExceptions import InvalidPresentationUrlError, InvalidSongIdError, InvalidSongFieldError
from .MalachiExceptions import InvalidServiceUrlError, MalformedServiceFileError, UnspecifiedServiceUrl
from .MalachiExceptions import InvalidVideoUrlError
from .MalachiExceptions import MissingStyleParameterError
from .MalachiExceptions import QLCConnectionError, LightingBlockedError

class MalachiServer():

    def __init__(self):
        self.SOCKETS = set()
        self.LIGHT_STATE_SOCKETS = set()
        self.DISPLAY_STATE_SOCKETS = set()
        self.STYLE_STATE_SOCKETS = set()
        self.APP_SOCKETS = set()
        self.MEDIA_SOCKETS = set()
        self.CAPOS = dict()
        self.screen_state = "on"
        self.s = Service()
        self.tracker = Tracker()
        self.ph = PresentationHandler()
        self.light_preset_list, self.light_channel_list = self.load_light_presets()
        self.lh = LightHandler(self.light_channel_list)
        self.style_list, self.current_style = self.load_styles()

    def register(self, websocket, path):
        # Use path to determine and store type of socket in SOCKETS
        self.SOCKETS.add((websocket, path[1:]))
        self.CAPOS[websocket] = 0
        # Register socket capabilities
        if path[1:] in ["app"]:
            self.APP_SOCKETS.add((websocket, path[1:]))
        if path[1:] in ["display", "app"]:
            self.STYLE_STATE_SOCKETS.add((websocket, path[1:]))
            self.MEDIA_SOCKETS.add((websocket, path[1:]))
        if path[1:] in ["leader", "display", "app"]:
            self.DISPLAY_STATE_SOCKETS.add((websocket, path[1:]))
        if path[1:] in ["lights", "app"]:
            self.LIGHT_STATE_SOCKETS.add((websocket, path[1:]))
        
    def unregister(self, websocket, path):
        # websocket has been closed by client
        self.SOCKETS.remove((websocket, path[1:]))
        if websocket in self.CAPOS:
            del self.CAPOS[websocket]
        if path[1:] in ["app"]:
            self.APP_SOCKETS.remove((websocket, path[1:]))
        if path[1:] in ["display", "app"]:
            self.STYLE_STATE_SOCKETS.remove((websocket, path[1:]))
            self.MEDIA_SOCKETS.remove((websocket, path[1:]))
        if path[1:] in ["leader", "display", "app"]:
            self.DISPLAY_STATE_SOCKETS.remove((websocket, path[1:]))
        if path[1:] in ["lights", "app"]:
            self.LIGHT_STATE_SOCKETS.remove((websocket, path[1:]))

    def key_check(self, key_dict, required_keys):
        missing_keys = ""
        for key in required_keys:
            if key not in key_dict:
                missing_keys = missing_keys + key + " "
        return missing_keys

    async def basic_init(self, websocket):
        await websocket.send(json.dumps({
            "action" : "update.basic-init",
            "params" : json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
            }))

    async def leader_init(self, websocket):
        await websocket.send(json.dumps({
            "action" : "update.leader-init",
            "params" : json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
            }))

    async def display_init(self, websocket):
        service_data = json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
        service_data['style'] = self.style_list[self.current_style]
        await websocket.send(json.dumps({
            "action" : "update.display-init",
            "params" : service_data
            }))

    async def app_init(self, websocket):
        service_data = json.loads(self.s.to_JSON_full())
        service_data['style'] = self.style_list[self.current_style]
        service_data['style-list'] = self.style_list
        service_data['current-style'] = self.current_style
        service_data['light-preset-list'] = self.light_preset_list
        await websocket.send(json.dumps({
            "action" : "update.app-init",
            "params" : service_data
            }))

    async def light_init(self, websocket):
        try:
            light_data = self.lh.get_channels()
        except QLCConnectionError as e:
            light_data = []
        finally:
            await websocket.send(json.dumps({
                "action": "update.light-init",
                "params": { 
                    "channels": light_data,
                    "light-preset-list": self.light_preset_list
                }}))

    async def responder(self, websocket, path):
        # Websocket is opened by client
        self.register(websocket, path)

        # Send initial data packet based on path
        initial_data_switcher =  {
            "basic": self.basic_init,
            "leader": self.leader_init,
            "display": self.display_init,
            "app": self.app_init,
            "lights": self.light_init
        }
        if path[1:] in initial_data_switcher:
            initial_func = initial_data_switcher.get(path[1:], lambda: "None")
            await initial_func(websocket)

        try:
            # Websocket message loop
            command_switcher = {
                # Syntax: "command_name": [function, [params_needed]]
                "command.next-slide": [self.next_slide, []],
                "command.previous-slide": [self.previous_slide, []],
                "command.goto-slide": [self.goto_slide, ["index"]],
                "command.next-item": [self.next_item, []],
                "command.previous-item": [self.previous_item, []],
                "command.goto-item": [self.goto_item, ["index"]],
                "command.add-bible-item": [self.add_bible_item, ["version", "start-verse", "end-verse"]],
                "command.add-song-item": [self.add_song_item, ["song-id"]],
                "command.add-presentation": [self.add_presentation, ["url"]],
                "command.add-video": [self.add_video, ["url"]],
                "command.remove-item": [self.remove_item, ["index"]],
                "command.move-item": [self.move_item, ["from-index", "to-index"]],
                "command.set-display-state": [self.set_display_state, ["state"]],
                "command.new-service": [self.new_service, ["force"]],
                "command.load-service": [self.load_service, ["filename", "force"]],
                "command.save-service": [self.save_service, []],
                "command.save-service-as": [self.save_service_as, ["filename"]],
                "command.set-current-style": [self.set_current_style, ["index"]],
                "command.rename-style": [self.rename_style, ["index", "name"]],
                "command.delete-style": [self.delete_style, ["index"]],
                "command.add-style": [self.add_style, ["style"]],
                "command.edit-style": [self.edit_style, ["index", "style"]],
                "command.set-light-channel": [self.set_light_channel, ["channel", "value"]],
                "command.set-light-channels": [self.set_light_channels, ["channels"]],
                "command.get-light-channels": [self.get_light_channels, []],
                "command.fade-light-channels": [self.fade_light_channels, ["end-channels"]], 
                "command.blackout-lights": [self.blackout_lights, []],
                "command.unblackout-lights": [self.unblackout_lights, []],
                "command.save-preset": [self.save_preset, []],
                "command.create-song": [self.create_song, ["title", "fields"]],
                "command.edit-song": [self.edit_song, ["song-id", "fields"]],
                "command.play-video": [self.play_video, []],
                "command.pause-video": [self.pause_video, []],
                "command.stop-video": [self.stop_video, []],
                "command.seek-video": [self.seek_video, ["seconds"]],
                "client.set-capo": [self.set_capo, ["capo"]],
                "query.bible-by-text": [self.bible_text_query, ["version", "search-text"]],
                "query.bible-by-ref": [self.bible_ref_query, ["version", "search-ref"]],
                "query.song-by-text": [self.song_text_query, ["search-text"]],
                "request.full-song": [self.request_full_song, ["song-id"]],
                "request.bible-versions": [self.request_bible_versions, []],
                "request.bible-books": [self.request_bible_books, ["version"]],
                "request.chapter-structure": [self.request_chapter_structure, ["version"]],
                "request.all-presentations": [self.request_all_presentations, []],
                "request.all-videos": [self.request_all_videos, []],
                "request.all-services": [self.request_all_services, []],
                "request.all-styles": [self.request_all_styles, []],
                "request.all-presets": [self.request_all_presets, []]
            }
            async for message in websocket:
                try:
                    json_data = json.loads(message)
                    # Check json_data has action and params keys
                    k_check = self.key_check(json_data, ["action", "params"])
                    if k_check == "":
                        command_item = command_switcher.get(json_data["action"])
                        if command_item != None:
                            # Check that all required parameters have been supplied
                            p_check = self.key_check(json_data["params"], command_item[1])
                            if p_check == "":
                                await command_item[0](websocket, json_data["params"])
                            else:
                                await self.server_response(websocket, "error.json", "missing-params", json_data["action"] + ": " + p_check)
                        else:
                            # Invalid command
                            await self.server_response(websocket, "error.json", "invalid-command", json_data["action"])
                    else:
                        # Malformed JSON
                        await self.server_response(websocket, "error.json", "missing-keys", k_check)
                except JSONDecodeError:
                    await self.server_response(websocket, "error.json", "decode-error", message)
        finally:
            # Websocket is closed by client
            self.unregister(websocket, path)

    # Update functions
    async def clients_slide_index_update(self):
        for socket in self.SOCKETS:
            await socket[0].send(json.dumps({
                "action" : "update.slide-index-update", 
                "params" : {
                    "item_index": self.s.item_index, 
                    "slide_index": self.s.slide_index
                    }
                }))

    async def clients_item_index_update(self):
        for socket in self.SOCKETS:
            if len(self.s.items) == 0:
                cur_item = {}
            else:
                cur_item = json.loads(self.s.items[self.s.item_index].to_JSON(self.CAPOS[socket[0]]))
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
            await socket[0].send(json.dumps({
                "action" : "update.service-overview-update", 
                "params" : json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[socket[0]]))
                }))

    # Lighting commands
    async def set_light_channel(self, websocket, params):
        status, details = "ok", ""
        try:
            channel, value = params["channel"], params["value"]
            self.lh.set_channel(channel, value)
            for socket in self.LIGHT_STATE_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.light-channel-update", 
                    "params" : {
                        "channel": channel,
                        "value": value
                    }
                }))
        except QLCConnectionError as e:
            status, details = "no-connection", e.msg
        except LightingBlockedError as e:
            status, details = "lighting-blocked", e.msg
        finally:
            await self.server_response(websocket, "response.set-light-channel", status, details)

    async def set_light_channels(self, websocket, params):
        status, details = "ok", ""
        try:
            self.lh.set_channels(params["channels"])
            for socket in self.LIGHT_STATE_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.light-channels-update", 
                    "params" : {
                        "channels": params["channels"]
                    }
                }))
        except QLCConnectionError as e:
            status, details = "no-connection", e.msg
        except LightingBlockedError as e:
            status, details = "lighting-blocked", e.msg
        finally:
            await self.server_response(websocket, "response.set-light-channels", status, details)

    async def get_light_channels(self, websocket, params):
        status, details = "ok", ""
        try:
            details = self.lh.get_channels()
        except QLCConnectionError as e:
            status, details = "no-connection", e.msg
        except LightingBlockedError as e:
            status, details = "lighting-blocked", e.msg
        finally:
            await websocket.send(json.dumps({
                "action": "result.get-light-channels",
                "params": {
                    "status": status,
                    "details": details
                }
            }))

    async def fade_light_channels(self, websocket, params):
        status, details = "ok", ""
        try:
            fade_thread = threading.Thread(target=self.lh.fade_channels, args=(params["end-channels"], 4000))
            fade_thread.start()
            for socket in self.LIGHT_STATE_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.fade-update", 
                    "params" : {
                        "channels": params["end-channels"],
                        "duration": 4000
                    }
                }))
        except QLCConnectionError as e:
            status, details = "no-connection", e.msg
        except LightingBlockedError as e:
            status, details = "lighting-blocked", e.msg
        finally:
            await self.server_response(websocket, "response.fade-light-channels", status, details)

    async def blackout_lights(self, websocket, params):
        status, details = "ok", ""
        try:
            self.lh.save_fixture_channels()
            fade_thread = threading.Thread(target=self.lh.fade_channels, args=(self.lh.blackout_channels, 4000))
            fade_thread.start()
            for socket in self.LIGHT_STATE_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.fade-update", 
                    "params" : {
                        "channels": self.lh.blackout_channels,
                        "duration": 4000
                    }
                }))
        except QLCConnectionError as e:
            status, details = "no-connection", e.msg
        except LightingBlockedError as e:
            status, details = "lighting-blocked", e.msg
        finally:
            await self.server_response(websocket, "response.blackout-lights", status, details)

    async def unblackout_lights(self, websocket, params):
        status, details = "ok", ""
        try:
            fade_thread = threading.Thread(target=self.lh.fade_channels, args=(self.lh.saved_channels, 4000))
            fade_thread.start()
            for socket in self.LIGHT_STATE_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.fade-update", 
                    "params" : {
                        "channels": self.lh.saved_channels,
                        "duration": 4000
                    }
                }))
        except QLCConnectionError as e:
            status, details = "no-connection", e.msg
        except LightingBlockedError as e:
            status, details = "lighting-blocked", e.msg
        finally:
            await self.server_response(websocket, "response.unblackout-lights", status, details)

    async def save_preset(self, websocket, params):
        status, details = "ok", ""
        try:
            preset = self.lh.get_channels()
            self.light_preset_list.append(preset)
            self.save_light_presets()
            for socket in self.LIGHT_STATE_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.light-preset-list-update", 
                    "params" : {
                        "list-preset-list": self.light_preset_list
                    }
                }))
        except QLCConnectionError as e:
            status, details = "no-connection", e.msg
        finally:
            await self.server_response(websocket, "response.save-preset", status, details)

    async def create_song(self, websocket, params):
        status, details = "ok", ""
        try:
            details = Song.create_song(params["title"], params["fields"])
        except InvalidSongFieldError as e:
            status, details = "invalid-field", e.msg
        finally:
            await self.server_response(websocket, "respose.create-song", status, details)

    async def edit_song(self, websocket, params):
        status, details = "ok", ""
        try:
            Song.edit_song(int(params["song-id"]), params["fields"])
            for i in range(len(self.s.items)):
                if type(self.s.items[i]) is Song:
                    if self.s.items[i].song_id == int(params["song-id"]):
                        # Refresh instance of edited Song in service
                        self.s.items[i].get_nonslide_data()
                        self.s.items[i].paginate_from_style(self.style_list[self.current_style])
            # Update all clients
            await self.clients_item_index_update()
        except InvalidSongIdError as e:
            status, details = "invalid-id", e.msg
        except InvalidSongFieldError as e:
            status, details = "invalid-field", e.msg
        except MissingStyleParameterError as e:
            status, details = "invalid-style", e.msg
        finally:
            await self.server_response(websocket, "response.edit-song", status, details)

    # Command functions
    async def next_slide(self, websocket, params):
        status, details = "ok", ""
        result = self.update_impress_next_effect()
        if result == -1:
            # We are not on a presentation, so advance slide as normal
            s_result = self.s.next_slide()
            if s_result == 1:
                await self.clients_slide_index_update()
            elif s_result == 0:
                status, details = "invalid-index", "Already at last slide"
            else:
                status = "no-current-item"
        else:
            # We are showing a presentation, so update service slide index based on result
            self.s.set_slide_index(result)
            await self.clients_slide_index_update()
        await self.server_response(websocket, "response.next-slide", status, details)

    async def previous_slide(self, websocket, params):
        status, details = "ok", ""
        result = self.update_impress_previous_effect()
        if result == -1:
            # We are not on a presentation, so advance slide as normal
            s_result = self.s.previous_slide()
            if s_result == 1:
                await self.clients_slide_index_update()
            elif s_result == 0:
                status, details = "invalid-index", "Already at first slide"
            else:
                status = "no-current-item"
        else:
            # We are showing a presentation, so update service slide index based on result
            self.s.set_slide_index(result)
            await self.clients_slide_index_update()
        await self.server_response(websocket, "response.previous-slide", status, details)

    async def goto_slide(self, websocket, params):
        status, details = "ok", ""
        self.update_impress_goto_slide(int(params["index"]))
        s_result = self.s.set_slide_index(int(params["index"]))
        if s_result == 1:
            await self.clients_slide_index_update()
        elif s_result == 0:
            status, details = "invalid-index", "Index out of bounds error"
        else:
            status = "no-current-item"
        await self.server_response(websocket, "response.goto-slide", status, details)

    async def next_item(self, websocket, params):
        status, details = "ok", ""
        if self.s.next_item():
            self.track_usage()
            self.update_impress_change_item()
            await self.clients_item_index_update()
        else:
            status, details = "invalid-index", "Already at last index"
        await self.server_response(websocket, "response.next-item", status, details)

    async def previous_item(self, websocket, params):
        status, details = "ok", ""
        if self.s.previous_item():
            self.track_usage()
            self.update_impress_change_item()
            await self.clients_item_index_update()
        else:
            status, details = "invalid-index", "Already at first index"
        await self.server_response(websocket, "response.previous-item", status, details)

    async def goto_item(self, websocket, params):
        status, details = "ok", ""
        if self.s.set_item_index(int(params["index"])):
            self.track_usage()
            self.update_impress_change_item()
            await self.clients_item_index_update()
        else:
            status, details = "invalid-index", "Index out of bounds error"
        await self.server_response(websocket, "response.goto-item", status, details)

    async def remove_item(self, websocket, params):
        status, details = "ok", ""
        index = int(params["index"])
        result = self.s.remove_item_at(index)
        if result == True:
            if index == self.s.item_index:
                # Current item was removed
                if self.s.item_index > 0:
                    self.s.item_index -= 1
                    self.track_usage()
                elif len(self.s.items) == 0:
                    self.s.item_index = -1
                    self.s.slide_index = -1
                self.update_impress_change_item()
            elif index < self.s.item_index:
                self.s.item_index -= 1
            await self.clients_service_items_update()
        else:
            status, details = "invalid-index", str(index)
        await self.server_response(websocket, "response.remove-item", status, details)

    async def move_item(self, websocket, params):
        status, details = "ok", ""
        f_index, t_index = int(params["from-index"]), int(params["to-index"])
        result = self.s.move_item(f_index, t_index)
        if result == 1:
            # Currently selected item was the item moved
            if f_index == self.s.item_index:
                if f_index < t_index:
                    self.s.item_index = t_index - 1
                else:
                    self.s.item_index = t_index
            # Position of currently selected item was affected by the move
            elif f_index < t_index and self.s.item_index > f_index and self.s.item_index <= t_index:
                self.s.item_index -= 1
            elif t_index < f_index and self.s.item_index >= t_index and self.s.item_index < f_index:
                self.s.item_index += 1
        elif result == 0:
            details = "No need to move items"
        elif result == -1:
            status = "invalid-index"
            if f_index < 0 or f_index >= len(self.s.items):
                details = "from-index (" + str(f_index) + ") "
            if t_index < 0 or t_index >= len(self.s.items):
                details = details + "to-index (" + str(t_index) + ") "
        await self.clients_service_items_update()
        await self.server_response(websocket, "response.move-item", status, details)

    async def add_bible_item(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.add_item(BiblePassage(
                params["version"], 
                params["start-verse"], 
                params["end-verse"],
                self.style_list[self.current_style]))
        except InvalidVersionError as e:
            status, details = "invalid-version", e.msg
        except InvalidVerseIdError as e:
            status, details = "invalid-verse", e.msg
        finally:
            await self.server_response(websocket, "response.add-bible-item", status, details)
            await self.clients_service_items_update()

    async def add_song_item(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.add_item(Song(params["song-id"], self.style_list[self.current_style]))
        except InvalidSongIdError as e:
            status, details = "invalid-song", e.msg
        finally:
            await self.server_response(websocket, "response.add-song-item", status, details)
            await self.clients_service_items_update()

    async def add_presentation(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.add_item(Presentation(params["url"]))
        except InvalidPresentationUrlError as e:
            status, details = "invalid-presentation", e.msg
        finally:
            await self.server_response(websocket, "response.add-presentation", status, details)
            await self.clients_service_items_update()

    async def add_video(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.add_item(Video(params["url"]))
        except InvalidVideoUrlError as e:
            status, details = "invalid-video", e.msg
        finally:
            await self.server_response(websocket, "response.add-video", status, details)
            await self.clients_service_items_update()

    async def set_display_state(self, websocket, params):
        self.screen_state = params["state"]
        for socket in self.DISPLAY_STATE_SOCKETS:
            await socket[0].send(json.dumps({
                "action" : "update.display-state", 
                "params" : {
                    "state": self.screen_state
                    }
                }))
        self.update_impress_screen_state()
        await self.server_response(websocket, "response.set-display-state", "ok", "")

    async def new_service(self, websocket, params):
        status = "ok"
        if self.s.modified == False or params["force"] == True:
            self.s = Service()
            await self.clients_service_items_update()
        else:
            status = "unsaved-service"
        await self.server_response(websocket, "response.new-service", status, "")

    async def load_service(self, websocket, params):
        status, details = "ok", ""
        if self.s.modified == False or params["force"] == True:
            try:
                self.s.load_service(params["filename"], self.style_list[self.current_style])
            except InvalidServiceUrlError as e:
                self.s = Service()
                status, details = "invalid-url", e.msg
            except MalformedServiceFileError as e:
                self.s = Service()
                status, details = "malformed-json", e.msg
            finally:
                await self.server_response(websocket, "response.load-service", status, details)
                await self.clients_service_items_update()
        else:
            await self.server_response(websocket, "response.load-service", "unsaved-service", "")
        
    async def save_service(self, websocket, params):
        status, details = "ok", ""
        try:
            self.s.save()
        except UnspecifiedServiceUrl as e:
            status, details = "unspecified-service", e.msg
        finally:
            await self.server_response(websocket,"response.save-service", status, details)

    async def save_service_as(self, websocket, params):
        self.s.save_as(params["filename"])
        await self.server_response(websocket, "response.save-service", "ok", "")

    async def set_current_style(self, websocket, params):
        status, details = "ok", ""
        index = int(params["index"])
        if index >= 0 and index < len(self.style_list):
            self.current_style = index
            for i in range(len(self.s.items)):
                if type(self.s.items[i]) is Song or type(self.s.items[i]) is BiblePassage:
                    self.s.items[i].paginate_from_style(self.style_list[self.current_style])
            for socket in self.STYLE_STATE_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.style-update", 
                    "params" : {
                        "style": self.style_list[self.current_style]
                        }
                    }))
            await self.clients_item_index_update()
        else:
            status, details = "invalid-index", "Index out of bounds error"
        await self.server_response(websocket, "response.set-current-style", status, details)

    async def rename_style(self, websocket, params):
        status, details= "ok", ""
        index = int(params["index"])
        if index >= 0 and index < len(self.style_list):
            self.style_list[index]["name"] = params["name"]
            self.save_styles()
            for socket in self.APP_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.style-list-update", 
                    "params" : {
                        "styles": self.style_list,
                        "index": self.current_style
                        }
                    }))
        else:
            status, details = "invalid-index", "Indexout of bounds error"
        await self.server_response(websocket, "response.rename-style", status, details)

    async def add_style(self, websocket, params):
        status, details = "ok", self.key_check(params["style"], ["name", "params"])
        if details != "":
            status = "invalid-json"
            details = "Missing style key(s): " + details
        else:
            self.style_list.append(params["style"])
            self.save_styles()
            for socket in self.APP_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.style-list-update", 
                    "params" : {
                        "styles": self.style_list,
                        "index": self.current_style
                        }
                    }))
        await self.server_response(websocket, "response.rename-style", status, details)

    async def delete_style(self, websocket, params):
        status, details = "ok", ""
        index = int(params["index"])
        if index >= 0 and index < len(self.style_list) and index != self.current_style:
            self.style_list.pop(index) # Delete style from list
            if self.current_style > index:
                self.current_style = self.current_style - 1
            self.save_styles()
            for socket in self.APP_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "update.style-list-update", 
                    "params" : {
                        "styles": self.style_list,
                        "index": self.current_style
                        }
                    }))
        else:
            if index == self.current_style:
                status, details = "invalid-index", "Can't delete currently selected style"
            else:
                status, details = "invalid-index", "Index out of bounds"
        await self.server_response(websocket, "response.delete-style", status, details)

    async def edit_style(self, websocket, params):
        status, details = "ok", self.key_check(params["style"], ["name", "params"])
        if details != "":
            status = "invalid-json"
            details = "Missing style key(s): " + details
        else:
            index = int(params["index"])
            if index >= 0 and index < len(self.style_list):
                self.style_list[index] = params["style"]
                self.save_styles()
                for socket in self.APP_SOCKETS:
                    await socket[0].send(json.dumps({
                        "action" : "update.style-list-update", 
                        "params" : {
                            "styles": self.style_list,
                            "index": self.current_style
                            }
                        }))
            else:
                status, details = "invalid-index", "Index out of bounds"
        await self.server_response(websocket, "response.rename-style", status, details)

    async def play_video(self, websocket, params):
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            for socket in self.MEDIA_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "trigger.play-video", 
                    "params" : {}
                    }))
        else:
            status, details = "invalid-item", "Current service item is not a video"
        await self.server_response(websocket, "response.play-video", status, details)

    async def pause_video(self, websocket, params):
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            for socket in self.MEDIA_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "trigger.pause-video", 
                    "params" : {}
                    }))
        else:
            status, details = "invalid-item", "Current service item is not a video"
        await self.server_response(websocket, "response.pause-video", status, details)

    async def stop_video(self, websocket, params):
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            for socket in self.MEDIA_SOCKETS:
                await socket[0].send(json.dumps({
                    "action" : "trigger.stop-video", 
                    "params" : {}
                    }))
        else:
            status, details = "invalid-item", "Current service item is not a video"
        await self.server_response(websocket, "response.stop-video", status, details)

    async def seek_video(self, websocket, params):
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            sec = int(params["seconds"])
            if 0 <= sec and sec <= self.s.items[self.s.item_index].get_duration():
                for socket in self.MEDIA_SOCKETS:
                    await socket[0].send(json.dumps({
                        "action" : "trigger.seek-video",
                        "params" : {
                            "seconds": int(params["seconds"])
                        }
                    }))
            else:
                status, details = "invalid-time", "Invalid seek time: " + str(params["seconds"])
        else:
            status, details = "invalid-item", "Current service item is not a video"
        await self.server_response(websocket, "response.seek-video", status, details)

    # Server response function
    async def server_response(self, websocket, action, status, details):
        await websocket.send(json.dumps({
            "action" : action, 
            "params" : {
                "status": status,
                "details": details
                }
            }))

    # Client functions - response to client only
    async def set_capo(self, websocket, params):
        self.CAPOS[websocket] = int(params["capo"])
        if len(self.s.items) == 0:
            cur_item = {}
        else:
            cur_item = json.loads(self.s.items[self.s.item_index].to_JSON(self.CAPOS[websocket]))
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
        status, verses = "ok", []
        try:
            verses = json.loads(BiblePassage.text_search(params["version"], params["search-text"]))
        except InvalidVersionError:
            status = "invalid-version"
        except (InvalidReferenceError, MalformedReferenceError):
            status = "invalid-reference"
        finally:
            await websocket.send(json.dumps({
                "action": "result.bible-verses",
                "params": {
                    "status": status,
                    "verses": verses
                }}))

    async def bible_ref_query(self, websocket, params):
        status, verses = "ok", []
        try:
            verses = json.loads(BiblePassage.ref_search(params["version"], params["search-ref"]))
        except InvalidVersionError:
            status = "invalid-version"
        except (InvalidReferenceError, MalformedReferenceError):
            status = "invalid-reference"
        finally:
            await websocket.send(json.dumps({
                "action": "result.bible-verses",
                "params": {
                    "status": status,
                    "verses": verses
                }}))

    async def song_text_query(self, websocket, params):
        result = Song.text_search(params["search-text"])
        await websocket.send(json.dumps({
            "action": "result.song-titles",
            "params": {
                "songs": json.loads(result)
            }}))

    # Other client requests
    async def request_full_song(self, websocket, params):
        status, data = "ok", {}
        try:
            data = json.loads(Song(params["song-id"], self.style_list[self.current_style]).to_JSON_full_data())
        except InvalidSongIdError:
            status = "invalid-id"
        finally:
            await websocket.send(json.dumps({
                "action": "result.song-details",
                "params": {
                    "status": status,
                    "song-data": data
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
        status, books = "ok", []
        try:
            books = BiblePassage.get_books(params["version"]) 
        except InvalidVersionError:
            status = "invalid-version"
        finally:
            await websocket.send(json.dumps({
                "action": "result.bible-books",
                "params": {
                    "status": status,
                    "books": books
                }
            }))

    async def request_chapter_structure(self, websocket, params):
        status, chapters = "ok", []
        try:
            chapters = BiblePassage.get_chapter_structure(params["version"])
        except InvalidVersionError:
            status = "invalid-version"
        finally:
            await websocket.send(json.dumps({
                "action": "result.chapter-structure",
                "params": {
                    "status": status,
                    "chapter-structure": chapters
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

    async def request_all_videos(self, websocket, params):
        urls = Video.get_all_videos()
        await websocket.send(json.dumps({
            "action": "result.all-videos",
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

    async def request_all_styles(self, websocket, params):
        await websocket.send(json.dumps({
            "action": "result.all-styles",
            "params": {
                "styles": self.style_list
            }
        }))

    async def request_all_presets(self, websocket, params):
        await websocket.send(json.dumps({
            "action": "result.all-presets",
            "params": {
                "presets": self.light_preset_list
            }
        }))

    # Song usage tracking
    def track_usage(self):
        if self.s.get_current_item_type() == "Song":
            self.tracker.log(self.s.items[self.s.item_index].song_id)

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

    def load_styles(self):
        with open("./styles/global_styles.json") as f:
            json_data = json.load(f)
        return json_data["styles"], json_data["default_index"]

    def save_styles(self):
        json_data = {}
        json_data["styles"] = self.style_list
        json_data["default_index"] = self.current_style
        with open("./styles/global_styles.json", "w") as f:
            f.write(json.dumps(json_data, indent=2))

    def load_light_presets(self):
        with open("./lights/light_presets.json") as f:
            json_data = json.load(f)
        return json_data["presets"], json_data["channels"]

    def save_light_presets(self):
        json_data = {}
        json_data["channels"] = self.light_channel_list
        json_data["presets"] = self.light_preset_list
        with open("./lights/light_presets.json", "w") as f:
            f.write(json.dumps(json_data))