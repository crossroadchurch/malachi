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
import threading
import subprocess
from websockets.exceptions import ConnectionClosed
import cv2
import pyautogui
from Service import Service
from BiblePassage import BiblePassage
from Song import Song
from Presentation import Presentation
from LightHandler import LightHandler
from Video import Video
from Tracker import Tracker
from ScreenCapturer import ScreenCapturer
from MalachiExceptions import InvalidVersionError, InvalidVerseIdError
from MalachiExceptions import MalformedReferenceError, MatchingVerseIdError, UnknownReferenceError
from MalachiExceptions import InvalidSongIdError, InvalidSongFieldError
from MalachiExceptions import InvalidServiceUrlError, MalformedServiceFileError
from MalachiExceptions import InvalidVideoUrlError, UnspecifiedServiceUrl
from MalachiExceptions import MissingStyleParameterError, MissingDataFilesError
from MalachiExceptions import InvalidPresentationUrlError
from MalachiExceptions import QLCConnectionError, LightingBlockedError

class MalachiServer():
    """
    Handle all Malachi websocket requests and keep clients informed
    of appropriate state changes
    """

    LIGHT_PRESET_FILE = "./lights/light_presets.json"
    SONGS_DATABASE = "./data/songs.sqlite"
    GLOBAL_STYLE_FILE = "./data/global_style.json"
    BIBLE_VERSIONS_FILES = "./data/bible_versions.json"

    def __init__(self):
        try:
            self.light_preset_list, self.light_channel_list = [], []
            self.bible_versions = [] # Loaded within check_data_files()
            self.screen_style = []
            self.video_loop = ""
            self.loop_width, self.loop_height = 0, 0
            self.check_data_files()
            Video.generate_video_thumbnails()
            self.SOCKETS = set()
            self.LIGHT_STATE_SOCKETS = set()
            self.DISPLAY_STATE_SOCKETS = set()
            self.STYLE_STATE_SOCKETS = set()
            self.APP_SOCKETS = set()
            self.MEDIA_SOCKETS = set()
            self.MONITOR_SOCKETS = set()
            self.CAPOS = dict()
            self.screen_state = "off"
            self.s = Service()
            self.load_light_presets()
            self.lh = LightHandler(self.light_channel_list)
            self.scap = ScreenCapturer(self, 1)
            self.load_style()
        except MissingDataFilesError as crit_error:
            raise MissingDataFilesError(crit_error.msg[51:]) from crit_error

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
        if path[1:] in ["lights", "app"]:
            self.LIGHT_STATE_SOCKETS.add((websocket, path[1:]))
        if path[1:] in ["monitor", "leader"]:
            self.MONITOR_SOCKETS.add((websocket, path[1:]))

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
        if path[1:] in ["lights", "app"]:
            self.LIGHT_STATE_SOCKETS.remove((websocket, path[1:]))
        if path[1:] in ["monitor", "leader"]:
            self.MONITOR_SOCKETS.remove((websocket, path[1:]))

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
            "action" : "update.basic-init",
            "params" : json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
            }))

    async def leader_init(self, websocket):
        """Send initialisation message to new leader client"""
        service_data = json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
        service_data['screen_state'] = self.screen_state
        await websocket.send(json.dumps({
            "action" : "update.leader-init",
            "params" : service_data
            }))

    async def display_init(self, websocket):
        """Send initialisation message to new display client"""
        service_data = json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[websocket]))
        service_data['style'] = self.screen_style
        service_data['screen_state'] = self.screen_state
        service_data['video_loop'] = self.video_loop
        service_data['loop-width'] = self.loop_width
        service_data['loop-height'] = self.loop_height
        await websocket.send(json.dumps({
            "action" : "update.display-init",
            "params" : service_data
            }))

    async def app_init(self, websocket):
        """Send initialisation message to new app client"""
        service_data = json.loads(self.s.to_JSON_full())
        service_data['style'] = self.screen_style
        service_data['light_preset_list'] = self.light_preset_list
        service_data['screen_state'] = self.screen_state
        service_data['video_loop'] = self.video_loop
        service_data['loop-width'] = self.loop_width
        service_data['loop-height'] = self.loop_height
        await websocket.send(json.dumps({
            "action" : "update.app-init",
            "params" : service_data
            }))

    async def light_init(self, websocket):
        """Send initialisation message to new light client"""
        try:
            light_data = self.lh.get_channels()
        except QLCConnectionError:
            light_data = []
        finally:
            await websocket.send(json.dumps({
                "action": "update.light-init",
                "params": {
                    "channels": light_data,
                    "light-preset-list": self.light_preset_list
                }}))

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
                "command.add-bible-item": [self.add_bible_item, \
                    ["version", "start-verse", "end-verse"]],
                "command.change-bible-version": [self.change_bible_version, ["version"]],
                "command.add-song-item": [self.add_song_item, ["song-id"]],
                "command.add-video": [self.add_video, ["url"]],
                "command.add-presentation": [self.add_presentation, ["url"]],
                "command.remove-item": [self.remove_item, ["index"]],
                "command.move-item": [self.move_item, ["from-index", "to-index"]],
                "command.set-display-state": [self.set_display_state, ["state"]],
                "command.new-service": [self.new_service, ["force"]],
                "command.load-service": [self.load_service, ["filename", "force"]],
                "command.save-service": [self.save_service, []],
                "command.save-service-as": [self.save_service_as, ["filename"]],
                "command.edit-style-param": [self.edit_style_param, ["param", "value"]],
                "command.set-loop": [self.set_loop, ["url"]],
                "command.clear-loop": [self.clear_loop, []],
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
                "command.start-presentation": [self.start_presentation, []],
                "command.stop-presentation": [self.stop_presentation, []],
                "command.next-presentation-slide": [self.next_presentation_slide, []],
                "command.prev-presentation-slide": [self.prev_presentation_slide, []],
                "command.transpose-up": [self.transpose_up, []],
                "command.transpose-down": [self.transpose_down, []],
                "command.transpose-by": [self.transpose_by, ["amount"]],
                "command.start-capture": [self.start_capture, ["monitor"]],
                "command.stop-capture": [self.stop_capture, []],
                "command.change-capture-monitor": [self.change_capture_monitor, ["monitor"]],
                "client.set-capo": [self.set_capo, ["capo"]],
                "query.bible-by-text": [self.bible_text_query, ["version", "search-text"]],
                "query.bible-by-ref": [self.bible_ref_query, ["version", "search-ref"]],
                "query.song-by-text": [self.song_text_query, ["search-text"]],
                "request.full-song": [self.request_full_song, ["song-id"]],
                "request.bible-versions": [self.request_bible_versions, []],
                "request.bible-books": [self.request_bible_books, ["version"]],
                "request.chapter-structure": [self.request_chapter_structure, ["version"]],
                "request.all-videos": [self.request_all_videos, []],
                "request.all-loops": [self.request_all_loops, []],
                "request.all-services": [self.request_all_services, []],
                "request.all-presets": [self.request_all_presets, []],
                "request.all-presentations": [self.request_all_presentations, []]
            }
            try:
                async for message in websocket:
                    try:
                        json_data = json.loads(message)
                        # Check json_data has action and params keys
                        k_check = MalachiServer.key_check(json_data, ["action", "params"])
                        if k_check == "":
                            command_item = command_switcher.get(json_data["action"])
                            if command_item is not None:
                                # Check that all required parameters have been supplied
                                p_check = MalachiServer.key_check(json_data["params"], \
                                    command_item[1])
                                if p_check == "":
                                    await command_item[0](websocket, json_data["params"])
                                else:
                                    await self.server_response(websocket, "error.json", \
                                        "missing-params", json_data["action"] + ": " + p_check)
                            else:
                                # Invalid command
                                await self.server_response(websocket, "error.json", \
                                    "invalid-command", json_data["action"])
                        else:
                            # Malformed JSON
                            await self.server_response(websocket, \
                                "error.json", "missing-keys", k_check)
                    except JSONDecodeError:
                        await self.server_response(websocket, "error.json", "decode-error", message)
            except ConnectionClosed as e:
                if e.reason:
                    print("ConnectionClosed exception: " + str(e.code) + ", " + str(e.reason))
                else:
                    print("ConnectionClosed exception: " + str(e.code) + ", no reason provided")
        finally:
            # Websocket is closed by client
            self.unregister(websocket, path)

    # Update functions
    async def clients_slide_index_update(self):
        """
        Send an update message to all sockets following a change to the value
        of the currently selected slide index in the service.
        """
        for socket in self.SOCKETS:
            await socket[0].send(json.dumps({
                "action" : "update.slide-index-update",
                "params" : {
                    "item_index": self.s.item_index,
                    "slide_index": self.s.slide_index
                    }
                }))

    async def clients_item_index_update(self):
        """
        Send an update message to all clients following a change to the value
        of the currently selected item in the service.
        """
        for socket in self.SOCKETS:
            if not self.s.items:
                cur_item = {}
            else:
                cur_item = json.loads(self.s.items[self.s.item_index]\
                    .to_JSON(self.CAPOS[socket[0]]))
            await socket[0].send(json.dumps({
                "action" : "update.item-index-update",
                "params" : {
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
                "action" : "update.service-overview-update",
                "params" : json.loads(self.s.to_JSON_titles_and_current(self.CAPOS[socket[0]]))
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
        for socket in self.MONITOR_SOCKETS:
            await socket[0].send(json.dumps({
                "action" : "update.stop-capture",
                "params" : {}
            }))
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

    async def capture_update(self, capture_url, capture_w, capture_h):
        """
        Send update to all monitor clients following the production of a new screen capture image.
        """
        for socket in self.MONITOR_SOCKETS:
            await socket[0].send(json.dumps({
                "action" : "update.capture-update",
                "params" : {"capture_url": capture_url, "width": capture_w, "height": capture_h}
            }))

    # Lighting commands
    async def set_light_channel(self, websocket, params):
        """
        Set value of a single lighting channel and send update message to appropriate clients.

        Arguments:
        params["channel"] -- the lighting channel to set
        params["value"] -- the new value for the lighting channel
        """
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
        """
        Set values of multiple lighting channels and send update message to appropriate clients.

        Arguments:
        params["channels"] -- a list of [channel number, new value] pairs
        """
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
        """Retrieve the current values of the lighting channels and send this data to websocket"""
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
        """
        Perform a lighting fade and send update message to appropriate clients.

        Arguments:
        params["end-channels"] -- a list of [channel number, end value] pairs, representing
        the state of the lighting at the end of the fade
        """
        status, details = "ok", ""
        try:
            fade_thread = threading.Thread(target=self.lh.fade_channels, \
                args=(params["end-channels"], 4000))
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
        """
        Perform a faded blackout on the lighting and send update message to appropriate clients.
        The pre-fade values of the lighting channels are saved and can be restored by calling
        unblackout_lights.
        """
        status, details = "ok", ""
        try:
            self.lh.save_fixture_channels()
            fade_thread = threading.Thread(target=self.lh.fade_channels, \
                args=(self.lh.blackout_channels, 4000))
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
        """
        Perform a faded unblackout on the lighting and send update message to appropriate clients.
        The lighting channels will be restored to the values saved when blackout_lights was called.
        """
        status, details = "ok", ""
        try:
            fade_thread = threading.Thread(target=self.lh.fade_channels, \
                args=(self.lh.saved_channels, 4000))
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
        """
        Save the current lighting setup as a new lighting preset and send a message containing
        the updated lighting preset list to appropriate clients.
        """
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
        s_result = self.s.next_slide()
        if s_result == 1:
            await self.clients_slide_index_update()
        elif s_result == 0:
            status, details = "invalid-index", "Already at last slide"
        else:
            status = "no-current-item"
        await self.server_response(websocket, "response.next-slide", status, details)

    async def previous_slide(self, websocket, params):
        """Advance to previous slide and send update to appropriate clients."""
        status, details = "ok", ""
        s_result = self.s.previous_slide()
        if s_result == 1:
            await self.clients_slide_index_update()
        elif s_result == 0:
            status, details = "invalid-index", "Already at first slide"
        else:
            status = "no-current-item"
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
            self.s.add_item(BiblePassage(
                params["version"],
                params["start-verse"],
                params["end-verse"],
                self.screen_style,
                self.bible_versions))
        except InvalidVersionError as e:
            status, details = "invalid-version", e.msg
        except InvalidVerseIdError as e:
            status, details = "invalid-verse", e.msg
        finally:
            await self.server_response(websocket, "response.add-bible-item", status, details)
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
                new_start = BiblePassage.translate_verse_id(\
                    old_start, old_version, new_version, self.bible_versions)
                new_end = BiblePassage.translate_verse_id(\
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
                            len(re.findall("<sup>", new_passage.slides[new_slide_index]))
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
            self.s.add_item(Song(params["song-id"], self.screen_style))
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
            self.s.add_item(Video(params["url"]))
        except InvalidVideoUrlError as e:
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
            self.s.add_item(Presentation(params["url"]))
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
        for socket in self.DISPLAY_STATE_SOCKETS:
            await socket[0].send(json.dumps({
                "action" : "update.display-state",
                "params" : {
                    "state": self.screen_state
                    }
                }))
        await self.server_response(websocket, "response.set-display-state", "ok", "")

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
        params["filename"] -- the service to load, specified relative to the Malachi root.
        params["force"] -- carry out action even if current service is unsaved (boolean).
        """
        status, details = "ok", ""
        if not self.s.modified or params["force"]:
            try:
                self.s.load_service(params["filename"], self.screen_style, self.bible_versions)
            except InvalidServiceUrlError as e:
                self.s = Service()
                status, details = "invalid-url", e.msg
            except MalformedServiceFileError as e:
                self.s = Service()
                status, details = "malformed-json", e.msg
            except MissingStyleParameterError as e:
                self.s = Service()
                status, details = "invalid-style", e.msg
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
                    self.s.items[i].paginate_from_style(self.screen_style)
            await self.clients_service_items_update()
            self.save_style()
            for socket in self.STYLE_STATE_SOCKETS:
                await socket[0].send(json.dumps({
                    "action": "update.style-update",
                    "params": {
                        "style": self.screen_style
                    }
                }))
        else:
            status, details = "invalid-param", "Invalid style parameter: " + params["param"]
        await self.server_response(websocket, "response.edit-style-param", status, details)

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
            self.loop_width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.loop_height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
            for socket in self.MEDIA_SOCKETS:
                await socket[0].send(json.dumps({
                    "action": "update.video-loop",
                    "params":  {
                        "url": self.video_loop,
                        "loop-width": self.loop_width,
                        "loop-height": self.loop_height
                    }
                }))
        else:
            status, details = "invalid-url", "Specified url doesn't exist or is not a video"
        await self.server_response(websocket, "response.set-loop", status, details)

    async def clear_loop(self, websocket, params):
        """ Clear the current video loop background and send update to appropriate clients. """
        status, details = "ok", ""
        self.video_loop = ""
        self.loop_width, self.loop_height = 0, 0
        for socket in self.MEDIA_SOCKETS:
            await socket[0].send(json.dumps({
                "action": "update.video-loop",
                "params":  {
                    "url": self.video_loop,
                    "loop-width": self.loop_width,
                    "loop-height": self.loop_height
                }
            }))
        await self.server_response(websocket, "response.clear-loop", status, details)

    async def play_video(self, websocket, params):
        """Send a message to appropriate clients triggering playback of the current Video."""
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
        """Send a message to appropriate clients pausing playback of the current Video."""
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
        """Send a message to appropriate clients stopping playback of the current Video."""
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
        """
        Send a message to appropriate clients to seek to a specified time within the current Video.

        Arguments:
        params["seconds"] -- the time, in seconds, to seek to within the Video.
        """
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Video":
            sec = int(params["seconds"])
            if 0 <= sec <= self.s.items[self.s.item_index].get_duration():
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

    async def start_presentation(self, websocket, params):
        """Call LibreOffice to start the presentation of the current service item."""
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Presentation":
            idx = self.s.item_index
            url = self.s.items[idx].get_url()
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

    async def transpose_up(self, websocket, params):
        """Transpose the current song up by one semitone and update appropriate clients."""
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Song":
            idx = self.s.item_index
            new_transpose = (self.s.items[idx].transpose_by + 1) % 12
            Song.edit_song(self.s.items[idx].song_id, {"transpose_by": new_transpose})
            # Refresh song in service
            self.s.items[idx].get_nonslide_data()
            self.s.items[idx].paginate_from_style(self.screen_style)
            # Update all clients
            await self.clients_item_index_update()
        else:
            status, details = "invalid-item", "Current service item is not a song"
        await self.server_response(websocket, "response.transpose-up", status, details)

    async def transpose_down(self, websocket, params):
        """Transpose the current song down by one semitone and update appropriate clients."""
        status, details = "ok", ""
        if self.s.get_current_item_type() == "Song":
            idx = self.s.item_index
            new_transpose = (self.s.items[idx].transpose_by - 1) % 12
            Song.edit_song(self.s.items[idx].song_id, {"transpose_by": new_transpose})
            # Refresh song in service
            self.s.items[idx].get_nonslide_data()
            self.s.items[idx].paginate_from_style(self.screen_style)
            # Update all clients
            await self.clients_item_index_update()
        else:
            status, details = "invalid-item", "Current service item is not a song"
        await self.server_response(websocket, "response.transpose-down", status, details)

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
            "action" : action,
            "params" : {
                "status": status,
                "details": details
                }
            }))

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
            verses = json.loads(BiblePassage.text_search(params["version"], \
                params["search-text"], self.bible_versions))
        except InvalidVersionError:
            status = "invalid-version"
        except MalformedReferenceError:
            status = "invalid-reference"
        finally:
            await websocket.send(json.dumps({
                "action": "result.bible-verses",
                "params": {
                    "status": status,
                    "verses": verses
                }}))

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
            verses = json.loads(BiblePassage.ref_search(params["version"], \
                params["search-ref"], self.bible_versions))
        except InvalidVersionError as search_e:
            status, details = "invalid-version", search_e.msg
        except MalformedReferenceError as search_e:
            status, details = "invalid-reference", search_e.msg
        except UnknownReferenceError as search_e:
            status, details = "unknown-reference", search_e.msg
        finally:
            await websocket.send(json.dumps({
                "action": "result.bible-verses",
                "params": {
                    "status": status,
                    "details": details,
                    "verses": verses
                }}))

    async def song_text_query(self, websocket, params):
        """
        Perform a text query on the song database and return a list of
        matching songs to websocket.  See Song.text_search for full
        details of the list that is returned from the query.

        Arguments:
        params["search-text"] -- the text to search for, in either the
        Song title or lyrics
        """
        result = Song.text_search(params["search-text"])
        await websocket.send(json.dumps({
            "action": "result.song-titles",
            "params": {
                "songs": json.loads(result)
            }}))

    # Other client requests
    async def request_full_song(self, websocket, params):
        """
        Return a JSON object containing all of the data for a specific Song to websocket.

        Arguments:
        params["song-id"] -- the id of the Song being requested.
        """
        status, data = "ok", {}
        try:
            data = json.loads(Song(params["song-id"], self.screen_style).to_JSON_full_data())
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
        """Return a list of all supported Bible versions to websocket."""
        await websocket.send(json.dumps({
            "action": "result.bible-versions",
            "params": {
                "versions": self.bible_versions
            }
        }))

    async def request_bible_books(self, websocket, params):
        """
        Return a list of all Bible books in a specified version of the Bible to websocket.

        Arguments:
        params["version"] -- the Bible version to use.
        """
        status, books = "ok", []
        try:
            books = BiblePassage.get_books(params["version"], self.bible_versions)
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
        """
        Return the chapter structure of the specified version of the Bible to websocket.
        The structure is returned as a list of tuples, each tuple of the form
        [book name, number of chapters]

        Arguments:
        version -- the Bible version to use.
        """
        status, chapters = "ok", []
        try:
            chapters = BiblePassage.get_chapter_structure(params["version"], self.bible_versions)
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

    async def request_all_videos(self, websocket, params):
        """Return a list of all video URLs in the ./videos directory to websocket."""
        urls = Video.get_all_videos()
        await websocket.send(json.dumps({
            "action": "result.all-videos",
            "params": {
                "urls": urls
            }
        }))

    async def request_all_loops(self, websocket, params):
        """Return a list of all video URKS in the ./loops directory to websocket."""
        urls = ['./loops/' + f for f in os.listdir('./loops')
                if f.endswith('.mpg') or f.endswith('mp4') or f.endswith('mov')]
        await websocket.send(json.dumps({
            "action": "result.all-loops",
            "params": {
                "urls": urls
            }
        }))

    async def request_all_services(self, websocket, params):
        """Return a list of all services in the ./services directory to websocket."""
        fnames = Service.get_all_services()
        await websocket.send(json.dumps({
            "action": "result.all-services",
            "params": {
                "filenames": fnames
            }
        }))

    async def request_all_presets(self, websocket, params):
        """Return a list of all lighting presets to websocket."""
        await websocket.send(json.dumps({
            "action": "result.all-presets",
            "params": {
                "presets": self.light_preset_list
            }
        }))

    async def request_all_presentations(self, websocket, params):
        """Return a list of all presentations in the ./presentations directory to websocket."""
        fnames = Presentation.get_all_presentations()
        await websocket.send(json.dumps({
            "action": "result.all-presentations",
            "params": {
                "urls": fnames
            }
        }))

    # Song usage tracking
    def track_usage(self):
        """Register usage of the current item, if it is a Song, in the tracking database."""
        if self.s.get_current_item_type() == "Song":
            Tracker.log(self.s.items[self.s.item_index].song_id)

    def load_style(self):
        """Load style information from ./data/global_style.json"""
        with open(MalachiServer.GLOBAL_STYLE_FILE) as f:
            json_data = json.load(f)
        self.screen_style = json_data["style"]

    def save_style(self):
        """Save style information to ./data/global_style.json"""
        json_data = {}
        json_data["style"] = self.screen_style
        with open(MalachiServer.GLOBAL_STYLE_FILE, "w") as f:
            f.write(json.dumps(json_data, indent=2))

    def load_light_presets(self):
        """Load lighting preset information from ./lights/light_presets.json"""
        with open(MalachiServer.LIGHT_PRESET_FILE) as f:
            json_data = json.load(f)
        self.light_preset_list = json_data["presets"]
        self.light_channel_list = json_data["channels"]

    def save_light_presets(self):
        """Save lighting preset information to ./lights/light_presets.json"""
        json_data = {}
        json_data["channels"] = self.light_channel_list
        json_data["presets"] = self.light_preset_list
        with open(MalachiServer.LIGHT_PRESET_FILE, "w") as f:
            f.write(json.dumps(json_data))

    def check_data_files(self):
        """
        Check that all essential data files exist.
        Those files deemed to be essential are the songs database, the JSON settings files
        for Bible versions, lighting presets and global style, and Bible databases referenced
        in the Bible versions JSON file.

        Possible exceptions:
        MissingDataFilesError - raised if any essential files are missing.
        """
        missing_files = []
        for f in [MalachiServer.BIBLE_VERSIONS_FILES, MalachiServer.SONGS_DATABASE,
                  MalachiServer.LIGHT_PRESET_FILE, MalachiServer.GLOBAL_STYLE_FILE]:
            if not os.path.isfile(f):
                missing_files.append(f)
        if missing_files:
            raise MissingDataFilesError(missing_files)
        self.load_bible_versions()
        for v in self.bible_versions:
            if not os.path.isfile("./data/" + v + ".sqlite"):
                missing_files.append("./data/" + v + ".sqlite")
        if missing_files:
            raise MissingDataFilesError(missing_files)

    def load_bible_versions(self):
        """Load supported Bible versions from ./data/bible_versions.json."""
        with open(MalachiServer.BIBLE_VERSIONS_FILES) as f:
            json_data = json.load(f)
        self.bible_versions = json_data["versions"]
