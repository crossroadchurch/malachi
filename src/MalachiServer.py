# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention
# pylint: disable=C0302 # Too many lines in module!
# pylint: disable=W0613 # Unused argument, due to having many params={}
# pylint: disable=R0904 # Too many public methods
# pylint: disable=R0902 # Too many instance attributes
# pylint: disable=R0914 # Too many local variables
# pylint: disable=R1705 # Unnecessary "else" after "return".  Disabled for code readability

"""
Handle all Malachi websocket requests and keep clients informed
of appropriate state changes
"""

import json
from json.decoder import JSONDecodeError
import os
import re
import shutil
import subprocess
from websockets.exceptions import ConnectionClosed
import cv2
import pyautogui
from Service import Service
from BiblePassage import BiblePassage
from Song import Song
from Presentation import Presentation
from Video import Video
from Background import Background
from Tracker import Tracker
from ScreenCapturer import ScreenCapturer
from MalachiExceptions import InvalidVersionError, InvalidVerseIdError
from MalachiExceptions import MalformedReferenceError, MatchingVerseIdError, UnknownReferenceError
from MalachiExceptions import InvalidSongIdError, InvalidSongFieldError
from MalachiExceptions import InvalidServiceUrlError, MalformedServiceFileError
from MalachiExceptions import InvalidVideoUrlError, InvalidVideoError, UnspecifiedServiceUrl
from MalachiExceptions import InvalidBackgroundUrlError
from MalachiExceptions import MissingStyleParameterError, MissingDataFilesError
from MalachiExceptions import InvalidPresentationUrlError


class MalachiServer():
    """
    Handle all Malachi websocket requests and keep clients informed
    of appropriate state changes
    """

    SONGS_DATABASE = "./data/songs.sqlite"
    GLOBAL_SETTINGS_FILE = "./data/global_settings.json"

    def __init__(self):
        try:
            Song.update_schema() # Check song database has up to date schema
            self.setup_commands()
            self.bible_versions = []  # Loaded within check_data_files()
            self.screen_style = []
            self.capture_refresh_rate = 1000
            self.video_loop = ""
            self.loop_width, self.loop_height = 0, 0
            self.check_data_files()
            Video.generate_video_thumbnails()
            Background.generate_background_thumbnails()
            self.SOCKETS = set()
            self.DISPLAY_STATE_SOCKETS = set()
            self.STYLE_STATE_SOCKETS = set()
            self.APP_SOCKETS = set()
            self.MEDIA_SOCKETS = set()
            self.MONITOR_SOCKETS = set()
            self.LOCKED_SOCKETS = set()
            self.CAPOS = dict()
            self.screen_state = "off"
            self.s = Service()
            self.scap = ScreenCapturer(self, 1)
            self.last_cap = ""
            self.load_settings()
        except MissingDataFilesError as crit_error:
            raise MissingDataFilesError(crit_error.msg[51:]) from crit_error

    def setup_commands(self):
        self.command_switcher = {
            # Syntax: "command_name": [function, [params_needed]]
            "command.next-slide": [self.next_slide, []],
            "command.previous-slide": [self.previous_slide, []],
            "command.goto-slide": [self.goto_slide, ["index"]],
            "command.next-item": [self.next_item, []],
            "command.previous-item": [self.previous_item, []],
            "command.goto-item": [self.goto_item, ["index"]],
            "command.add-bible-item": [self.add_bible_item, ["version", "start-verse", "end-verse"]],
            "command.change-bible-pl-version": [self.change_bible_pl_version, ["version"]],                      
            "command.remove-bible-pl-version": [self.remove_bible_pl_version, []],                   
            "command.change-bible-version": [self.change_bible_version, ["version"]],
            "command.add-song-item": [self.add_song_item, ["song-id"]],
            "command.add-video": [self.add_video, ["url"]],
            "command.add-presentation": [self.add_presentation, ["url"]],
            "command.remove-item": [self.remove_item, ["index"]],
            "command.move-item": [self.move_item, ["from-index", "to-index"]],
            "command.set-display-state": [self.set_display_state, ["state"]],
            "command.toggle-display-state": [self.toggle_display_state, []],
            "command.new-service": [self.new_service, ["force"]],
            "command.load-service": [self.load_service, ["filename", "force"]],
            "command.save-service": [self.save_service, []],
            "command.save-service-as": [self.save_service_as, ["filename"]],
            "command.export-service": [self.export_service, ["filename"]],
            "command.edit-style-param": [self.edit_style_param, ["param", "value"]],
            "command.edit-style-params": [self.edit_style_params, ["style_params"]],
            "command.set-loop": [self.set_loop, ["url"]],
            "command.clear-loop": [self.clear_loop, []],
            "command.restore-loop": [self.restore_loop, []],
            "command.create-song": [self.create_song, ["title", "fields"]],
            "command.edit-song": [self.edit_song, ["song-id", "fields"]],
            "command.play-video": [self.play_video, []],
            "command.pause-video": [self.pause_video, []],
            "command.stop-video": [self.stop_video, []],
            "command.seek-video": [self.seek_video, ["seconds"]],
            "command.play-audio": [self.play_audio, []],
            "command.pause-audio": [self.pause_audio, []],
            "command.stop-audio": [self.stop_audio, []],
            "command.start-presentation": [self.start_presentation, []],
            "command.stop-presentation": [self.stop_presentation, []],
            "command.next-presentation-slide": [self.next_presentation_slide, []],
            "command.prev-presentation-slide": [self.prev_presentation_slide, []],
            "command.generic-play": [self.generic_play, []],
            "command.generic-stop": [self.generic_stop, []],
            "command.transpose-by": [self.transpose_by, ["amount"]],
            "command.start-capture": [self.start_capture, ["monitor"]],
            "command.stop-capture": [self.stop_capture, []],
            "command.change-capture-monitor": [self.change_capture_monitor, ["monitor"]],
            "command.change-capture-rate": [self.change_capture_rate, ["rate"]],
            "command.unlock-socket": [self.unlock_socket, []],
            "command.start-countdown": [self.start_countdown, ["hr", "min"]],
            "command.clear-countdown": [self.clear_countdown, []],
            "client.set-capo": [self.set_capo, ["capo"]],
            "query.bible-by-text": [self.bible_text_query, ["version", "search-text"]],
            "query.bible-by-ref": [self.bible_ref_query, ["version", "search-ref"]],
            "query.song-by-text": [self.song_text_query, ["search-text", "remote"]],
            "request.full-song": [self.request_full_song, ["song-id"]],
            "request.bible-versions": [self.request_bible_versions, []],
            "request.bible-books": [self.request_bible_books, ["version"]],
            "request.chapter-structure": [self.request_chapter_structure, ["version"]],
            "request.all-videos": [self.request_all_videos, []],
            "request.all-loops": [self.request_all_loops, []],
            "request.all-backgrounds": [self.request_all_backgrounds, []],
            "request.all-services": [self.request_all_services, []],
            "request.all-presentations": [self.request_all_presentations, []],
            "request.all-audio": [self.request_all_audio, []],
            "request.capture-update": [self.capture_update, []]
        }

    def register(self, websocket, path):
        """
        Register a new websocket connection.

        Arguments:
        websocket -- the websocket connection object
        path -- the path used to connect this websocket eg /display, /app
        """
        # Use path to determine and store type of socket in SOCKETS
        self.SOCKETS.add((websocket, path[1:]))
        self.CAPOS[websocket] = 0
        # Register socket capabilities
        if path[1:] in ["app"]:
            self.APP_SOCKETS.add((websocket, path[1:]))
        if path[1:] in ["display", "app"]:
            self.STYLE_STATE_SOCKETS.add((websocket, path[1:]))
        if path[1:] in ["display", "app", "monitor"]:
            self.MEDIA_SOCKETS.add((websocket, path[1:]))
        if path[1:] in ["leader", "display", "app"]:
            self.DISPLAY_STATE_SOCKETS.add((websocket, path[1:]))
        if path[1:] in ["monitor", "leader"]:
            self.MONITOR_SOCKETS.add((websocket, path[1:]))
        print("Websocket registered: " + websocket.remote_address[0] + ":" +
              str(websocket.remote_address[1]) + " (" + path + ")")

    def unregister(self, websocket, path):
        """Unregister a websocket connection that has been closed by a client."""
        # websocket has been closed by client
        self.SOCKETS.remove((websocket, path[1:]))
        if websocket in self.CAPOS:
            del self.CAPOS[websocket]
        if path[1:] in ["app"]:
            self.APP_SOCKETS.remove((websocket, path[1:]))
        if path[1:] in ["display", "app"]:
            self.STYLE_STATE_SOCKETS.remove((websocket, path[1:]))
        if path[1:] in ["display", "app", "monitor"]:
            self.MEDIA_SOCKETS.remove((websocket, path[1:]))
        if path[1:] in ["leader", "display", "app"]:
            self.DISPLAY_STATE_SOCKETS.remove((websocket, path[1:]))
        if path[1:] in ["monitor", "leader"]:
            self.MONITOR_SOCKETS.remove((websocket, path[1:]))
        if websocket in self.LOCKED_SOCKETS:
            self.LOCKED_SOCKETS.remove(websocket)
        print("Websocket unregistered: " + websocket.remote_address[0] + ":" +
              str(websocket.remote_address[1]) + " (" + path + ")")

    @classmethod
    def key_check(cls, key_dict, required_keys):
        """
        Check whether a dictionary contains a set of keys.

        Arguments:
        key_dict -- the dictionary to check
        required_keys -- the list of keys to check for in key_dict

        Return value:
        A list containing those keys that do not exist in key_dict
        """
        missing_keys = ""
        for key in required_keys:
            if key not in key_dict:
                missing_keys = missing_keys + key + " "
        return missing_keys

    async def basic_init(self, websocket):
        """Send initialisation message to new basic client"""
        await websocket.send(json.dumps({
            "action": "update.basic-init",
            "params": json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
        }))

    async def leader_init(self, websocket):
        """Send initialisation message to new leader client"""
        service_data = json.loads(
            self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
        service_data['screen_state'] = self.screen_state
        await websocket.send(json.dumps({
            "action": "update.leader-init",
            "params": service_data
        }))

    async def display_init(self, websocket):
        """Send initialisation message to new display client"""
        service_data = json.loads(
            self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
        service_data['style'] = self.screen_style
        service_data['screen_state'] = self.screen_state
        service_data['video_loop'] = self.video_loop
        service_data['loop-width'] = self.loop_width
        service_data['loop-height'] = self.loop_height
        await websocket.send(json.dumps({
            "action": "update.display-init",
            "params": service_data
        }))

    async def app_init(self, websocket):
        """Send initialisation message to new app client"""
        service_data = json.loads(self.s.to_JSON_full())
        service_data['style'] = self.screen_style
        service_data['refresh_rate'] = self.capture_refresh_rate
        service_data['screen_state'] = self.screen_state
        service_data['video_loop'] = self.video_loop
        service_data['loop-width'] = self.loop_width
        service_data['loop-height'] = self.loop_height
        await websocket.send(json.dumps({
            "action": "update.app-init",
            "params": service_data
        }))

    async def handle_message(self, websocket, json_data):
        """Process message from websocket"""
        k_check = MalachiServer.key_check(json_data, ["action", "params"])
        if k_check != "": # Malformed JSON - missing key(s)
            await self.server_response(websocket, "error.json", "missing-keys", k_check)            
            return
        command_item = self.command_switcher.get(json_data["action"])
        if command_item is None: # Invalid command
            await self.server_response(websocket, "error.json", "invalid-command", json_data["action"])
            return
        p_check = MalachiServer.key_check(json_data["params"], command_item[1])
        if p_check != "": # Required parameter(s) missing
            await self.server_response(websocket, "error.json", "missing-params",
                                       json_data["action"] + ": " + p_check)    
            return
        # Execute the command
        await command_item[0](websocket, json_data["params"])

    async def responder(self, websocket, path):
        """
        Handle a websocket connection.
        This method handles the entire websocket lifecycle:
        On creation -- the websocket is registered.
        While alive -- messages received from the websocket are verified against
        a list of possible messages and then the appropriate server function is
        called.
        On closing -- the websocket is unregistered.

        Arguments:
        websocket -- the websocket connection object
        path -- the path used to connect this websocket eg /display, /app
        """
        # Websocket is opened by client
        self.register(websocket, path)

        # Send initial data packet based on path
        initial_data_switcher = {
            "basic": self.basic_init,
            "monitor": self.basic_init,
            "leader": self.leader_init,
            "display": self.display_init,
            "app": self.app_init
        }
        if path[1:] in initial_data_switcher:
            initial_func = initial_data_switcher.get(path[1:], lambda: "None")
            await initial_func(websocket)

        try:
            # Websocket message loop
            async for message in websocket:
                try:
                    json_data = json.loads(message)
                    await self.handle_message(websocket, json_data)
                except JSONDecodeError:
                    await self.server_response(websocket, "error.json", "decode-error", message)
        except ConnectionClosed as e:
            message = "ConnectionClosed exception from " + websocket.remote_address[0] + ":" + \
                str(websocket.remote_address[1]) + " (" + path + "): "
            if e.reason:
                print(message + str(e.code) + ", " + str(e.reason))
            else:
                print(message + str(e.code) + ", no reason provided")
        finally:
            # Websocket is closed by client
            self.unregister(websocket, path)

    # Update functions
    async def clients_slide_index_update(self):
        """
        Send an update message to all sockets following a change to the value
        of the currently selected slide index in the service.
        """
        await self.broadcast(self.SOCKETS, "update.slide-index-update", {
            "item_index": self.s.item_index,
            "slide_index": self.s.slide_index
        })

    async def clients_item_index_update(self):
        """
        Send an update message to all clients following a change to the value
        of the currently selected item in the service.
        """
        for socket in self.SOCKETS:
            if not self.s.items:
                cur_item = {}
            else:
                cur_item = json.loads(self.s.items[self.s.item_index]
                                      .to_JSON(self.CAPOS[socket[0]]))
            await socket[0].send(json.dumps({
                "action": "update.item-index-update",
                "params": {
                    "item_index": self.s.item_index,
                    "slide_index": self.s.slide_index,
                    "current_item": cur_item
                }
            }))

    async def clients_service_items_update(self):
        """
        Send an update message to all clients following a change to the
        items in the service plan.
        """
        for socket in self.SOCKETS:
            await socket[0].send(json.dumps({
                "action": "update.service-overview-update",
                "params": json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[socket[0]]))
            }))

    # Screen capture commands
    async def start_capture(self, websocket, params):
        """
        Start screen capture of the specified screen.

        Arguments:
        params["monitor"] -- the number of the monitor to capture (1 = main desktop, 2 = extended)
        """
        status, details = "ok", ""
        self.scap.stop()
        self.scap = ScreenCapturer(self, int(params["monitor"]))
        self.scap.start()
        await self.server_response(websocket, "response.start-capture", status, details)

    async def stop_capture(self, websocket, params):
        """Stop any active screen captures and inform any monitor clients."""
        status, details = "ok", ""
        self.scap.stop()
        await self.broadcast(self.MONITOR_SOCKETS, "update.stop-capture", {})
        await self.server_response(websocket, "response.stop-capture", status, details)

    async def change_capture_monitor(self, websocket, params):
        """
        Change the monitor that is being used for screen captures.

        Arguments:
        params["monitor"] -- the new monitor to capture from
        """
        status, details = "ok", ""
        self.scap.change_monitor(int(params["monitor"]))
        await self.server_response(websocket, "response.change-capture-monitor", status, details)

    async def change_capture_rate(self, websocket, params):
        """
        Change the capture rate that is being used for screen captures.

        Arguments:
        params["rate"] -- the new capture rate in milliseconds, must be in the range [200,5000]
        """
        status, details = "ok", ""
        rate = int(params["rate"])
        if 200 <= rate <= 5000:
            self.capture_refresh_rate = rate
            self.save_settings()
            await self.broadcast(self.APP_SOCKETS, "update.capture-rate", {
                "refresh_rate": self.capture_refresh_rate
            })
        else:
            status, details = "invalid-rate", "Capture rate must be in the range [200, 5000]"
        await self.server_response(websocket, "response.change-capture-rate", status, details)

    async def unlock_socket(self, websocket, params):
        """
        Unlock the current socket to allow it to receive further capture updates.
        """
        status, details = "ok", ""
        if websocket in self.LOCKED_SOCKETS:
            self.LOCKED_SOCKETS.remove(websocket)
        else:
            status, details = "unlock-error", "Socket was not locked"
        await self.server_response(websocket, "response.unlock-socket", status, details)

    async def capture_ready(self, capture_src):
        """
        Inform all monitor clients that a new capture is available.

        Arguments:
        capture_src -- the new capture image as a base64 URI.
        """
        self.last_cap = capture_src
        await self.broadcast(self.MONITOR_SOCKETS, "update.capture-ready", {})

    async def capture_update(self, websocket, params):
        """
        Send current captured image as a base64 URI to the specified websocket.
        """
        self.LOCKED_SOCKETS.add(websocket)
        await self.send_message(websocket, "result.capture-update", {
            "capture_src": self.last_cap,
            "width": self.scap.mon_w,
            "height": self.scap.mon_h
        })

    async def create_song(self, websocket, params):
        """
        Create a new Song in the songs database.
        The Song will only be added to the database if it passes all field validation checks.
        Not all song fields need to be provided at this point; at a minimum, just the song
        title is required.  See Song.edit_song for further details of required values for fields.

        Arguments:
        params["title"] -- the title for the Song
        params["fields"] -- dict of other Song fields to set when creating the Song; can be empty.
        """
        status, details = "ok", ""
        try:
            details = Song.create_song(params["title"], params["fields"])
        except InvalidSongFieldError as e:
            status, details = "invalid-field", e.msg
        finally:
            await self.server_response(websocket, "response.create-song", status, details)

    async def edit_song(self, websocket, params):
        """
        Edit a Song that exists in the songs database.  See Song.edit_song for further details
        of required values for fields.

        Arguments:
        params["song-id"] -- the id of the Song to be edited.
        params["fields"] -- dict of Song field values to be edited,
        not all fields need to be specified.
        """
        status, details = "ok", ""
        try:
            Song.edit_song(int(params["song-id"]), params["fields"])
            for i in range(len(self.s.items)):
                if isinstance(self.s.items[i], Song):
                    if self.s.items[i].song_id == int(params["song-id"]):
                        # Refresh instance of edited Song in service
                        self.s.items[i].get_nonslide_data()
                        self.s.items[i].paginate_from_style(self.screen_style)
                        self.s.items[i].add_fills()
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
        """Advance to next slide and send update to appropriate clients."""
        status, details = "ok", ""
        if self.s.get_current_item_type() in ["Song", "BiblePassage"]:
            s_result = self.s.next_slide()
            if s_result == 1:
                await self.clients_slide_index_update()
            elif s_result == 0:
                status, details = "invalid-index", "Already at last slide"
            else:
                status = "no-current-item"
        if self.s.get_current_item_type() == "Presentation":
            pyautogui.press("pagedown")
        await self.server_response(websocket, "response.next-slide", status, details)

    async def previous_slide(self, websocket, params):
        """Advance to previous slide and send update to appropriate clients."""
        status, details = "ok", ""
        if self.s.get_current_item_type() in ["Song", "BiblePassage"]:
            s_result = self.s.previous_slide()
            if s_result == 1:
                await self.clients_slide_index_update()
            elif s_result == 0:
                status, details = "invalid-index", "Already at first slide"
            else:
                status = "no-current-item"
        if self.s.get_current_item_type() == "Presentation":
            pyautogui.press("pageup")
        await self.server_response(websocket, "response.previous-slide", status, details)

    async def goto_slide(self, websocket, params):
        """
        Advance to specific slide and send update to appropriate clients.

        Arguments:
        params["index"] -- the slide index to advance to.
        """
        status, details = "ok", ""
        s_result = self.s.set_slide_index(int(params["index"]))
        if s_result == 1:
            await self.clients_slide_index_update()
        elif s_result == 0:
            status, details = "invalid-index", "Index out of bounds error"
        else:
            status = "no-current-item"
        await self.server_response(websocket, "response.goto-slide", status, details)

    async def next_item(self, websocket, params):
        """Advance to next service item and send update to appropriate clients."""
        status, details = "ok", ""
        if self.s.next_item():
            self.track_usage()
            await self.clients_item_index_update()
        else:
            status, details = "invalid-index", "Already at last index"
        await self.server_response(websocket, "response.next-item", status, details)

    async def previous_item(self, websocket, params):
        """Advance to previous service item and send update to appropriate clients."""
        status, details = "ok", ""
        if self.s.previous_item():
            self.track_usage()
            await self.clients_item_index_update()
        else:
            status, details = "invalid-index", "Already at first index"
        await self.server_response(websocket, "response.previous-item", status, details)

    async def goto_item(self, websocket, params):
        """
        Advance to specific service item and send update to appropriate clients.

        Arguments:
        params["index"] -- the index of the service item to advance to.
        """
        status, details = "ok", ""
        if self.s.set_item_index(int(params["index"])):
            self.track_usage()
            await self.clients_item_index_update()
        else:
            status, details = "invalid-index", "Index out of bounds error"
        await self.server_response(websocket, "response.goto-item", status, details)

    async def remove_item(self, websocket, params):
        """
        Remove an item from the service plan and send update to appropriate clients.

        Arguments:
        params["index"] -- the index of the item to remove.
        """
        status, details = "ok", ""
        index = int(params["index"])
        result = self.s.remove_item_at(index)
        if result:
            if index == self.s.item_index:
                # Current item was removed
                if self.s.item_index > 0:
                    self.s.item_index -= 1
                    self.s.slide_index = 0
                    self.track_usage()
                elif not self.s.items:
                    self.s.item_index = -1
                    self.s.slide_index = -1
            elif index < self.s.item_index:
                self.s.item_index -= 1
                self.s.slide_index = 0
            await self.clients_service_items_update()
        else:
            status, details = "invalid-index", str(index)
        await self.server_response(websocket, "response.remove-item", status, details)

    async def move_item(self, websocket, params):
        """
        Move an item within the service plan and send update to appropriate clients.

        Arguments:
        params["from-index"] -- the index of the item to move.
        params["to-index"] -- the index to move the item to within the current service.
        """
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
        """
        Add a BiblePassage to the service plan.

        Arguments:
        params["version"] -- the version of the Bible to use.
        params["start-verse"] -- the verse id at the start of the (inclusive) range.
        params["end-verse"] -- the verse id at the end of the (inclusive) range.
        """
        status, details = "ok", ""
        try:
            b = BiblePassage(
                params["version"],
                params["start-verse"],
                params["end-verse"],
                self.screen_style,
                self.bible_versions)
            self.s.add_item(b)
        except InvalidVersionError as e:
            status, details = "invalid-version", e.msg
        except InvalidVerseIdError as e:
            status, details = "invalid-verse", e.msg
        finally:
            await self.server_response(websocket, "response.add-bible-item", status, details)
            await self.clients_service_items_update()

    async def change_bible_pl_version(self, websocket, params):
        '''
        Change the parallel Bible version of the current item.

        Arguments:
        params["version"] -- the new parallel Bible version.
        '''
        status, details = "ok", ""
        try:
            if self.s.get_current_item_type() == "BiblePassage":
                self.s.items[self.s.item_index].parallel_paginate_from_style(
                    self.screen_style, params["version"], self.bible_versions)
            else:
                status, details = "invalid-item", "Current item not a Bible passage"
        except InvalidVersionError as e:
            status, details = "invalid-version", e.msg
        except InvalidVerseIdError as e:
            status, details = "invalid-verse", e.msg
        except MatchingVerseIdError as e:
            status, details = "invalid-matching-verse", e.msg
        finally:
            await self.server_response(websocket, "response.change-bible-pl-version", status, details)
            await self.clients_service_items_update()

    async def remove_bible_pl_version(self, websocket, params):
        '''
        Remove the parallel Bible version of the current item.
        '''
        status, details = "ok", ""
        try:
            if self.s.get_current_item_type() == "BiblePassage":
                self.s.items[self.s.item_index].paginate_from_style(self.screen_style)
            else:
                status, details = "invalid-item", "Current item not a Bible passage"
        finally:
            await self.server_response(websocket, "response.remove-bible-pl-version", status, details)
            await self.clients_service_items_update()

    async def change_bible_version(self, websocket, params):
        '''
        Change the Bible version of the current item.

        Arguments:
        params["version"] -- the new Bible version.
        '''
        status, details = "ok", ""
        try:
            if self.s.get_current_item_type() == "BiblePassage":
                old_version = self.s.items[self.s.item_index].version
                old_start = self.s.items[self.s.item_index].start_id
                old_end = self.s.items[self.s.item_index].end_id
                new_version = params["version"]
                new_start = BiblePassage.translate_verse_id(
                    old_start, old_version, new_version, self.bible_versions)
                new_end = BiblePassage.translate_verse_id(
                    old_end, old_version, new_version, self.bible_versions)
                new_passage = BiblePassage(
                    new_version, new_start, new_end,
                    self.screen_style, self.bible_versions)
                # Use slide_index to determine which verse is currently being displayed
                if self.s.slide_index > -1:
                    verse_count = 0
                    slides = self.s.items[self.s.item_index].slides
                    # Count number of verses before the current slide
                    for i in range(self.s.slide_index):
                        verse_count += len(re.findall("<sup>", slides[i]))
                    # Add 1 if there is (at least) a verse starting on the current slide
                    if re.findall("<sup>", slides[self.s.slide_index]):
                        verse_count += 1
                    # Find the slide in new_passage that contains the start of this verse
                    new_slide_index, new_verse_count = -1, 0
                    while new_verse_count < verse_count and \
                            new_slide_index < len(new_passage.slides):
                        new_slide_index += 1
                        new_verse_count += \
                            len(re.findall(
                                "<sup>", new_passage.slides[new_slide_index]))
                    self.s.slide_index = new_slide_index
                # Replace item in service with new passage
                del self.s.items[self.s.item_index]
                self.s.items.insert(self.s.item_index, new_passage)
                await self.clients_service_items_update()
            else:
                status, details = "invalid-item", "Current item not a Bible passage"
        except InvalidVersionError as e:
            status, details = "invalid-version", e.msg
        except InvalidVerseIdError as e:
            status, details = "invalid-verse", e.msg
        except MissingStyleParameterError as e:
            status, details = "invalid-style", e.msg
        except MatchingVerseIdError as e:
            status, details = "no-matching-verse", e.msg
        finally:
            await self.server_response(websocket, "response.change-bible-version", status, details)

    async def add_song_item(self, websocket, params):
        """
        Add a Song to the service plan.

        Arguments:
        params["song-id"] -- the id of the Song to add.
        """
        status, details = "ok", ""
        try:
            s = Song(params["song-id"], self.screen_style)
            self.s.add_item(s)
        except InvalidSongIdError as e:
            status, details = "invalid-song", e.msg
        finally:
            await self.server_response(websocket, "response.add-song-item", status, details)
            await self.clients_service_items_update()

    async def add_video(self, websocket, params):
        """
        Add a Video to the service plan.

        Arguments:
        params["url"] -- the URL of the Video to add, relative to the root of Malachi.
        """
        status, details = "ok", ""
        try:
            v = Video(params["url"])
            self.s.add_item(v)
        except InvalidVideoUrlError as e:
            status, details = "invalid-video", e.msg
        except InvalidVideoError as e:
            status, details = "invalid-video", e.msg
        finally:
            await self.server_response(websocket, "response.add-video", status, details)
            await self.clients_service_items_update()

    async def add_presentation(self, websocket, params):
        """
        Add a Presentation to the service plan.

        Arguments:
        params["url"] -- the URL of the Presentation to add, relative to the root of Malachi.
        """
        status, details = "ok", ""
        try:
            p = Presentation(params["url"])
            self.s.add_item(p)
        except InvalidPresentationUrlError as e:
            status, details = "invalid-presentation", e.msg
        finally:
            await self.server_response(websocket, "response.add-presentation", status, details)
            await self.clients_service_items_update()

    async def set_display_state(self, websocket, params):
        """
        Set the current display state and send update to appropriate clients.

        Arguments:
        params["state"] -- the new display state, can be "on" or "off".
        """
        self.screen_state = params["state"]
        await self.broadcast(self.DISPLAY_STATE_SOCKETS, "update.display-state", {
            "state": self.screen_state
        })
        await self.server_response(websocket, "response.set-display-state", "ok", "")

    async def toggle_display_state(self, websocket, params):
        """
        Toggle the current display state and send update to appropriate clients.
        """
        if self.screen_state == "on":
            new_state = "off"
        else:
            new_state = "on"
        self.screen_state = new_state
        await self.broadcast(self.DISPLAY_STATE_SOCKETS, "update.display-state", {
            "state": new_state
        })
        await self.server_response(websocket, "response.toggle-display-state", "ok", "")
        
    async def new_service(self, websocket, params):
        """
        Start a new Service and send update to appropriate clients.
        If the current service has been modified then the action will be blocked and the
        websocket making the request will be informed that the service is unsaved.  This
        behaviour cannot be overridden by setting params["force"] to True.

        Arguments:
        params["force"] -- carry out action even if current service is unsaved (boolean).
        """
        status = "ok"
        if not self.s.modified or params["force"]:
            self.s = Service()
            await self.clients_service_items_update()
        else:
            status = "unsaved-service"
        await self.server_response(websocket, "response.new-service", status, "")

    async def load_service(self, websocket, params):
        """
        Load a Service and send update to appropriate clients.
        If the current service has been modified then the action will be blocked and the
        websocket making the request will be informed that the service is unsaved.  This
        behaviour cannot be overridden by setting params["force"] to True.

        Arguments:
        params["filename"] -- the service to load relative to ./services.
        params["force"] -- carry out action even if current service is unsaved (boolean).
        """
        status, details = "ok", ""
        if not self.s.modified or params["force"]:
            try:
                if params["filename"][-4:] == "json":
                    self.s.load_service(
                        params["filename"], self.screen_style, self.bible_versions)
                elif params["filename"][-3:] == "zip":
                    self.s.import_service(
                        params["filename"], self.screen_style, self.bible_versions)
                else:
                    self.s = Service()
                    status, details = "invalid-url", "Could not find a service file at the url {url}".format(url=params["filename"])
            except InvalidServiceUrlError as e:
                self.s = Service()
                status, details = "invalid-url", e.msg
            except MalformedServiceFileError as e:
                self.s = Service()
                status, details = "malformed-json", e.msg
            except MissingStyleParameterError as e:
                self.s = Service()
                status, details = "invalid-style", e.msg
            except InvalidVersionError as e:
                self.s = Service()
                status, details = "invalid-version", e.msg
            except MalformedReferenceError as e:
                self.s = Service()
                status, details = "malformed-reference", e.msg
            except UnknownReferenceError as e:
                self.s = Service()
                status, details = "unknown-reference", e.msg
            finally:
                await self.server_response(websocket, "response.load-service", status, details)
                await self.clients_service_items_update()
        else:
            await self.server_response(websocket, "response.load-service", "unsaved-service", "")

    async def save_service(self, websocket, params):
        """Save the current service."""
        status, details = "ok", ""
        try:
            self.s.save()
        except UnspecifiedServiceUrl as e:
            status, details = "unspecified-service", e.msg
        finally:
            await self.server_response(websocket, "response.save-service", status, details)

    async def save_service_as(self, websocket, params):
        """
        Save the current service to a specified file.

        Arguments:
        params["filename"] -- the name of the save file, within the ./services directory.
        """
        self.s.save_as(params["filename"])
        await self.server_response(websocket, "response.save-service", "ok", "")

    async def export_service(self, websocket, params):
        """
        Export the current service to a specified zip file.

        Arguments:
        params["filename"] -- the name of the export zip file, within the ./services directory.
        """
        self.s.export_as(params["filename"])
        await self.server_response(websocket, "response.export-service", "ok", "")

    async def edit_style_param(self, websocket, params):
        """
        Edit a parameter of the screen style and send update to appropriate clients.

        Arguments:
        params["param"] -- the parameter to be edited.
        params["value"] -- the new value for the parameter.
        """
        status, details = "ok", ""
        if params["param"] in self.screen_style:
            self.screen_style[params["param"]] = params["value"]
            # Repaginate in new style
            for i in range(len(self.s.items)):
                if isinstance(self.s.items[i], Song):
                    self.s.items[i].get_nonslide_data()
                    self.s.items[i].paginate_from_style(self.screen_style)
                elif isinstance(self.s.items[i], BiblePassage):
                    if self.s.items[i].parallel_version == "":
                        self.s.items[i].paginate_from_style(self.screen_style)
                    else:
                        self.s.items[i].parallel_paginate_from_style(
                            self.screen_style,
                            self.s.items[i].parallel_version,
                            self.bible_versions)
            await self.clients_service_items_update()
            self.save_settings()
            await self.broadcast(self.STYLE_STATE_SOCKETS, "update.style-update", {
                "style": self.screen_style
            })
        else:
            status, details = "invalid-param", "Invalid style parameter: " + \
                params["param"]
        await self.server_response(websocket, "response.edit-style-param", status, details)

    async def edit_style_params(self, websocket, params):
        """
        Edit one or more parameters of the screen style and send update to appropriate clients.

        Arguments:
        params["style_params"] -- the array of parameters to be edited, each element of the form
          { "param": param_name, "value": new_value }.
        """
        status, details = "ok", ""
        invalid_params = []
        for style_param in params["style_params"]:
            if style_param["param"] in self.screen_style:
                self.screen_style[style_param["param"]] = style_param["value"]
            else:
                invalid_params.append(style_param["param"])
        if not invalid_params:
            # Repaginate in new style
            for i in range(len(self.s.items)):
                if isinstance(self.s.items[i], Song):
                    self.s.items[i].get_nonslide_data()
                    self.s.items[i].paginate_from_style(self.screen_style)
                elif isinstance(self.s.items[i], BiblePassage):
                    self.s.items[i].paginate_from_style(self.screen_style)
            await self.clients_service_items_update()
            self.save_settings()
            await self.broadcast(self.STYLE_STATE_SOCKETS, "update.style-update", {
                "style": self.screen_style
            })
        else:
            status, details = "invalid-params", "Invalid style parameters: " + \
                ', '.join(invalid_params)
        await self.server_response(websocket, "response.edit-style-params", status, details)

    async def set_loop(self, websocket, params):
        """
        Set the current video loop background and send update to appropriate clients.

        Arguments:
        params["url"] -- the new video loop background.
        """
        status, details = "ok", ""
        url = params["url"]
        if os.path.isfile(url) and \
                (url.endswith('.mpg') or url.endswith('mp4') or url.endswith('mov')):
            self.video_loop = url
            vid = cv2.VideoCapture(url)
            if vid.get(cv2.CAP_PROP_FPS) == 0:
                status, details = "invalid-loop", "Specified url {url} is not a valid video".format(url=url)
            else: 
                self.loop_width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.loop_height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
                await self.broadcast(self.MEDIA_SOCKETS, "update.video-loop", {
                    "url": self.video_loop,
                    "loop-width": self.loop_width,
                    "loop-height": self.loop_height
                })
        else:
            status, details = "invalid-url", "Specified url doesn't exist or is not a video"
        await self.server_response(websocket, "response.set-loop", status, details)

    async def clear_loop(self, websocket, params):
        """ Clear the current video loop background and send update to appropriate clients. """
        status, details = "ok", ""
        self.video_loop = ""
        self.loop_width, self.loop_height = 0, 0
        await self.broadcast(self.MEDIA_SOCKETS, "update.video-loop", {
            "url": self.video_loop,
            "loop-width": self.loop_width,
            "loop-height": self.loop_height
        })
        await self.server_response(websocket, "response.clear-loop", status, details)

    async def restore_loop(self, websocket, params):
        """ Send restore loop trigger to appropriate clients. """
        status, details = "ok", ""
        await self.broadcast(self.MEDIA_SOCKETS, "trigger.restore-loop", {})
        await self.server_response(websocket, "response.restore-loop", status, details)

    async def play_video(self, websocket, params):
        """Send a message to appropriate clients triggering playback of the current Video."""
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            await self.broadcast(self.MEDIA_SOCKETS, "trigger.play-video", {})
        else:
            status, details = "invalid-item", "Current service item is not a video"
        await self.server_response(websocket, "response.play-video", status, details)

    async def pause_video(self, websocket, params):
        """Send a message to appropriate clients pausing playback of the current Video."""
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            await self.broadcast(self.MEDIA_SOCKETS, "trigger.pause-video", {})
        else:
            status, details = "invalid-item", "Current service item is not a video"
        await self.server_response(websocket, "response.pause-video", status, details)

    async def stop_video(self, websocket, params):
        """Send a message to appropriate clients stopping playback of the current Video."""
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            await self.broadcast(self.MEDIA_SOCKETS, "trigger.stop-video", {})
        else:
            status, details = "invalid-item", "Current service item is not a video"
        await self.server_response(websocket, "response.stop-video", status, details)

    async def seek_video(self, websocket, params):
        """
        Send a message to appropriate clients to seek to a specified time within the current Video.

        Arguments:
        params["seconds"] -- the time, in seconds, to seek to within the Video.
        """
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            sec = int(params["seconds"])
            if 0 <= sec <= self.s.items[self.s.item_index].get_duration():
                await self.broadcast(self.MEDIA_SOCKETS, "trigger.seek-video", {
                    "seconds": int(params["seconds"])
                })
            else:
                status, details = "invalid-time", "Invalid seek time: " + \
                    str(params["seconds"])
        else:
            status, details = "invalid-item", "Current service item is not a video"
        await self.server_response(websocket, "response.seek-video", status, details)

    async def play_audio(self, websocket, params):
        """
        Send a message to appropriate clients triggering playback of audio associated
        with current Song.  Clients are responsible for error handling, failing gracefully
        if current item is not a song, or if the current song has no associated audio.
        """
        status, details = "ok", ""
        await self.broadcast(self.MEDIA_SOCKETS, "trigger.play-audio", {})
        await self.server_response(websocket, "response.play-audio", status, details)

    async def pause_audio(self, websocket, params):
        """
        Send a message to appropriate clients pausing playback of audio associated
        with current Song.  Clients are responsible for error handling, failing gracefully
        if current item is not a song, or if the current song has no associated audio.
        """
        status, details = "ok", ""
        await self.broadcast(self.MEDIA_SOCKETS, "trigger.pause-audio", {})
        await self.server_response(websocket, "response.pause-audio", status, details)

    async def stop_audio(self, websocket, params):
        """
        Send a message to appropriate clients stopping playback of audio associated
        with current Song.  Clients are responsible for error handling, failing gracefully
        if current item is not a song, or if the current song has no associated audio.
        """
        status, details = "ok", ""
        await self.broadcast(self.MEDIA_SOCKETS, "trigger.stop-audio", {})
        await self.server_response(websocket, "response.stop-audio", status, details)


    async def start_countdown(self, websocket, params):
        """
        Send a message to appropriate clients to start a countdown to a specified time.

        Arguments:
        params["hr"] -- the end hour of the countdown.
        params["min"] -- the end minute of the countdown.
        """
        status, details = "ok", ""
        hrs = int(params["hr"])
        mins = int(params["min"])
        if (0 <= mins < 60) and (0 <= hrs < 24):
            await self.broadcast(self.MEDIA_SOCKETS, "trigger.start-countdown", {
                "hr": int(params["hr"]),
                "min": int(params["min"])
            })
        else:
            status, details = "invalid-time", "Invalid countdown time: " + \
                str(params["hr"]) + ":" + str(params["min"])
        await self.server_response(websocket, "response.start-countdown", status, details)


    async def clear_countdown(self, websocket, params):
        """Send a message to clear any running countdown."""
        status, details = "ok", ""
        await self.broadcast(self.MEDIA_SOCKETS, "trigger.clear-countdown", {})
        await self.server_response(websocket, "response.clear-countdown", status, details)


    async def start_presentation(self, websocket, params):
        """Call LibreOffice to start the presentation of the current service item."""
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Presentation":
            # Check that soffice is accessible
            if shutil.which('soffice') is None:
                status, details = "no-soffice", "Couldn't access LibreOffice, please check Malachi installation instructions for more details"
            else:
                # Suspend any running loop
                await self.broadcast(self.MEDIA_SOCKETS, "trigger.suspend-loop", {})
                # Start presentation in LibreOffice
                url = self.s.items[self.s.item_index].get_url()
                subprocess.Popen(['soffice', '--show', url])
        else:
            status, details = "invalid-item", "Current service item is not a presentation"
        await self.server_response(websocket, "response.start-presentation", status, details)

    async def stop_presentation(self, websocket, params):
        """
        Generate keystroke to stop the current LibreOffice presentation.  This will fail if
        the LibreOffice presenter view does not have focus on the computer running the server.
        """
        status, details = "ok", ""
        pyautogui.press('escape')
        # Restore loop
        await self.broadcast(self.MEDIA_SOCKETS, "trigger.restore-loop", {})
        await self.server_response(websocket, "response.stop-presentation", status, details)

    async def next_presentation_slide(self, websocket, params):
        """
        Generate keystroke to advance to the next slide or animation in the current LibreOffice
        presentation.  This will fail if the LibreOffice presenter view does not have focus on the
        computer running the server.
        """
        status, details = "ok", ""
        pyautogui.press('pagedown')
        await self.server_response(websocket, "response.next-presentation-slide", status, details)

    async def prev_presentation_slide(self, websocket, params):
        """
        Generate keystroke to advance to the previous slide or animation in the current LibreOffice
        presentation.  This will fail if the LibreOffice presenter view does not have focus on the
        computer running the server.
        """
        status, details = "ok", ""
        pyautogui.press('pageup')
        await self.server_response(websocket, "response.prev-presentation-slide", status, details)

    async def generic_play(self, websocket, params):
        """
        Play the current service item - the actual action carried out depends on the type of
        service item.  The server response will be sent by the called function, rather than
        being of the form "response.generic-play".
        """
        if self.s.get_current_item_type() == "Presentation":
            await self.start_presentation(websocket, params)
        if self.s.get_current_item_type() == "Video":
            await self.play_video(websocket, params)
        if self.s.get_current_item_type() == "Song":
            await self.play_audio(websocket, params)

    async def generic_stop(self, websocket, params):
        """
        Stop playing the current service item - the actual action carried out depends on the type
        of service item.  The server response will be sent by the called function, rather than
        being of the form "response.generic-stop".
        """
        if self.s.get_current_item_type() == "Presentation":
            await self.stop_presentation(websocket, params)
        if self.s.get_current_item_type() == "Video":
            await self.stop_video(websocket, params)
        if self.s.get_current_item_type() == "Song":
            await self.stop_audio(websocket, params)

    async def transpose_by(self, websocket, params):
        """
        Transpose the current song up by a specified number of semitones and update
        appropriate clients.

        Arguments:
        params["amount"] -- the number of semitones to transpose up by.
        """
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Song":
            idx = self.s.item_index
            new_transpose = (self.s.items[idx].transpose_by + int(params["amount"])) % 12
            Song.edit_song(self.s.items[idx].song_id, {"transpose_by": new_transpose})
            # Refresh song in service
            self.s.items[idx].get_nonslide_data()
            self.s.items[idx].paginate_from_style(self.screen_style)
            self.s.items[idx].add_fills()
            # Update all clients
            await self.clients_item_index_update()
        else:
            status, details = "invalid-item", "Current service item is not a song"
        await self.server_response(websocket, "response.transpose-by", status, details)

    # Server response function
    async def server_response(self, websocket, action, status, details):
        """
        Send a message from the server to a websocket in response to an action.
        This will indicate whether the action has been successfully performed or details of the
        error that prevented the action from being performed.
        See github.com/crossroadchurch/malachi/wiki/WebSocket-messages for a full list of
        server responses.

        Arguments:
        websocket -- the websocket that made the action request.
        action -- the name of the response.  A command "command.do-something" will have a
        response called "response.do-something".
        status -- "ok" if the action was successfully performed, a short error code otherwise.
        details -- blank if the action was successfully performed, details of the error otherwise.
        """
        await websocket.send(json.dumps({
            "action": action,
            "params": {
                "status": status,
                "details": details
            }
        }))

    # Server broadcast functions
    async def broadcast(self, sockets, action, params):
        """Broadcast a message to a set of websocket clients."""
        for socket in sockets:
            await socket[0].send(json.dumps({"action": action, "params": params}))

    async def send_message(self, socket, action, params):
        """Broadcast a message to a single websocket client."""
        await socket.send(json.dumps({"action": action, "params": params}))

    # Client functions - response to client only
    async def set_capo(self, websocket, params):
        """
        Set the capo for a specific websocket and send update to this client.

        Arguments:
        params["capo"] -- the capo number for this client.
        """
        self.CAPOS[websocket] = int(params["capo"])
        if not self.s.items:
            cur_item = {}
        else:
            cur_item = json.loads(
                self.s.items[self.s.item_index].to_JSON(self.CAPOS[websocket]))
        await self.send_message(websocket, "update.item-index-update", {
                "item_index": self.s.item_index,
                "slide_index": self.s.slide_index,
                "current_item": cur_item
        })

    # Query functions - response to client only
    async def bible_text_query(self, websocket, params):
        """
        Perform a text query on a version of the Bible and return a list of
        matching verses to websocket.  See BiblePassage.text_search for full
        details of the list that is returned from the query.

        Arguments:
        params["version"] -- the version of the Bible to search
        params["search-text"] -- the text to search for
        """
        status, verses = "ok", []
        try:
            verses = json.loads(BiblePassage.text_search(params["version"],
                                                         params["search-text"], self.bible_versions))
        except InvalidVersionError:
            status = "invalid-version"
        except MalformedReferenceError:
            status = "invalid-reference"
        finally:
            await self.send_message(websocket, "result.bible-verses", {
                "status": status,
                "verses": verses
            })

    async def bible_ref_query(self, websocket, params):
        """
        Search for a passage within a version of the Bible and return a list of
        matching verses to websocket.  See BiblePassage.ref_search for full
        details of the list that is returned from the query.

        Arguments:
        params["version"] -- the version of the Bible to search
        params["search-ref"] -- the passage reference to search for
        """
        status, details, verses = "ok", "", []
        try:
            verses = json.loads(BiblePassage.ref_search(params["version"],
                                                        params["search-ref"], self.bible_versions))
        except InvalidVersionError as search_e:
            status, details = "invalid-version", search_e.msg
        except MalformedReferenceError as search_e:
            status, details = "invalid-reference", search_e.msg
        except UnknownReferenceError as search_e:
            status, details = "unknown-reference", search_e.msg
        finally:
            await self.send_message(websocket, "result.bible-verses", {
                "status": status,
                "details": details,
                "verses": verses
            })

    async def song_text_query(self, websocket, params):
        """
        Perform a text query on the song database and return a list of
        matching songs to websocket.  See Song.text_search for full
        details of the list that is returned from the query.

        Arguments:
        params["search-text"] -- the text to search for, in either the
        Song title or lyrics
        params["remote"] -- 0 = search local songs, 1 = search remote songs
        """
        result = Song.text_search(params["search-text"], params["remote"])
        await self.send_message(websocket, "result.song-titles", {
                "songs": json.loads(result)
        })

    # Other client requests
    async def request_full_song(self, websocket, params):
        """
        Return a JSON object containing all of the data for a specific Song to websocket.

        Arguments:
        params["song-id"] -- the id of the Song being requested.
        """
        status, data = "ok", {}
        try:
            data = json.loads(
                Song(params["song-id"], self.screen_style).to_JSON_full_data())
        except InvalidSongIdError:
            status = "invalid-id"
        finally:
            await self.send_message(websocket, "result.song-details", {
                "status": status,
                "song-data": data
            })

    async def request_bible_versions(self, websocket, params):
        """Return a list of all supported Bible versions to websocket."""
        await self.send_message(websocket, "result.bible-versions", {
            "versions": self.bible_versions
        })

    async def request_bible_books(self, websocket, params):
        """
        Return a list of all Bible books in a specified version of the Bible to websocket.

        Arguments:
        params["version"] -- the Bible version to use.
        """
        status, books = "ok", []
        try:
            books = BiblePassage.get_books(
                params["version"], self.bible_versions)
        except InvalidVersionError:
            status = "invalid-version"
        finally:
            await self.send_message(websocket, "result.bible-books", {
                "status": status,
                "books": books
            })

    async def request_chapter_structure(self, websocket, params):
        """
        Return the chapter structure of the specified version of the Bible to websocket.
        The structure is returned as a list of tuples, each tuple of the form
        [book name, number of chapters]

        Arguments:
        version -- the Bible version to use.
        """
        status, chapters = "ok", []
        try:
            chapters = BiblePassage.get_chapter_structure(
                params["version"], self.bible_versions)
        except InvalidVersionError:
            status = "invalid-version"
        finally:
            await self.send_message(websocket, "result.chapter-structure", {
                "status": status,
                "chapter-structure": chapters
            })

    async def request_all_videos(self, websocket, params):
        """Return a list of all video URLs in the ./videos directory to websocket."""
        urls = Video.get_all_videos()
        await self.send_message(websocket, "result.all-videos", {"urls": urls})

    async def request_all_loops(self, websocket, params):
        """Return a list of all video URLs in the ./loops directory to websocket."""
        urls = ['./loops/' + f for f in os.listdir('./loops')
                if f.endswith('.mpg') or f.endswith('mp4') or f.endswith('mov')]
        if urls:
            urls.sort()
        await self.send_message(websocket, "result.all-loops", {"urls": urls})

    async def request_all_backgrounds(self, websocket, params):
        """Return a list of all background URLs in the ./backgrounds directory to websocket."""
        bgs = [Background(url) for url in Background.get_all_backgrounds()]
        bg_json = [{"url": './backgrounds/' + bg.title, 
            "width": bg.image_width, "height": bg.image_height} for bg in bgs]
        await self.send_message(websocket, "result.all-backgrounds", {"bg_data": bg_json})

    async def request_all_services(self, websocket, params):
        """Return a list of all services in the ./services directory to websocket."""
        fnames = Service.get_all_services()
        await self.send_message(websocket, "result.all-services", {"filenames": fnames})

    async def request_all_presentations(self, websocket, params):
        """Return a list of all presentations in the ./presentations directory to websocket."""
        fnames = Presentation.get_all_presentations()
        await self.send_message(websocket, "result.all-presentations", {"urls": fnames})

    async def request_all_audio(self, websocket, params):
        """Return a list of all MP3 URLs in the ./audio directory to websocket."""
        urls = [f for f in os.listdir('./audio') if f.endswith('.mp3')]
        if urls:
            urls.sort()
        await self.send_message(websocket, "result.all-audio", {"urls": urls})

    # Song usage tracking
    def track_usage(self):
        """Register usage of the current item, if it is a Song, in the tracking database."""
        if self.s.get_current_item_type() == "Song":
            Tracker.log(self.s.items[self.s.item_index].song_id)

    def load_settings(self):
        """Load settings information from ./data/global_settings.json"""
        with open(MalachiServer.GLOBAL_SETTINGS_FILE) as f:
            json_data = json.load(f)
        self.screen_style = json_data["style"]
        self.capture_refresh_rate = json_data["capture_refresh"]

    def save_settings(self):
        """Save settings information to ./data/global_settings.json"""
        json_data = {}
        json_data["style"] = self.screen_style
        json_data["capture_refresh"] = self.capture_refresh_rate
        with open(MalachiServer.GLOBAL_SETTINGS_FILE, "w") as f:
            f.write(json.dumps(json_data, indent=2))

    def check_data_files(self):
        """
        Check that all essential data files exist.
        Those files deemed to be essential are the songs database, the JSON settings files
        for Bible versions and global style, and Bible databases referenced
        in the Bible versions JSON file.

        Possible exceptions:
        MissingDataFilesError - raised if any essential files are missing.
        """
        missing_files = []
        for f in [MalachiServer.SONGS_DATABASE, MalachiServer.GLOBAL_SETTINGS_FILE]:
            if not os.path.isfile(f):
                missing_files.append(f)
        if missing_files:
            raise MissingDataFilesError(missing_files)
        self.bible_versions = [f[:-7] for f in os.listdir('./data')
            if f.endswith('.sqlite') and f!='songs.sqlite']
        # Check that all Bible versions have word size data in the current style's font
        with open(MalachiServer.GLOBAL_SETTINGS_FILE) as f:
            json_data = json.load(f)
        font_file = json_data["style"]["font-file"]
        font_name = font_file[(font_file.rindex('/')+1):].split(".")[0]
        for version in self.bible_versions:
            if not os.path.isfile("./data/{v}_{f}.pkl".format(v=version,f=font_name)):
                print("Processing {v} version...".format(v=version), end=" ")
                BiblePassage.generate_word_sizes(version, font_file)
        # Load version pickles as class variable of BiblePassage
        BiblePassage.load_length_data(font_name, self.bible_versions)
        #Check that word size data for the song database exists in the current style's font
        Song.generate_word_sizes(font_file)
        Song.load_length_data(font_name)
        print("Malachi has loaded successfully!")
