# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention
# pylint: disable=R0912 # Too many branches
# pylint: disable=R1702 # Too many nested blocks
# pylint: disable=R1705 # Unnecessary "else" after "return".  Disabled for code readability

"""Represent a complete service plan in Malachi"""

import os
import glob
import json
from json import JSONDecodeError
from datetime import datetime
from zipfile import ZipFile
from BiblePassage import BiblePassage
from Song import Song
from Presentation import Presentation
from Video import Video
from MalachiExceptions import InvalidServiceUrlError, MalformedServiceFileError, \
    UnspecifiedServiceUrl, MissingStyleParameterError, InvalidVersionError, \
    MalformedReferenceError, UnknownReferenceError

class Service():
    """
    Represent a complete service plan in Malachi, with methods to
    navigate in the service plan, inform clients of changes to the
    service plan, and load/save the service plan.
    """

    def __init__(self):
        self.items = []
        self.item_index = -1
        self.slide_index = -1
        self.file_name = None
        self.modified = False

    def add_item(self, item):
        """
        Add an item to the end of the service plan.

        Arguments:
        item -- the item (Song, BiblePassage, Video, Presentation) to be added.
        """
        self.items.append(item)
        self.modified = True
        if len(self.items) == 1:
            self.item_index = 0 # Select first item added to service plan
            self.slide_index = 0
        self.autosave()

    def remove_item_at(self, index):
        """
        Remove item at the specified index from the service plan.

        Arguments:
        index -- the index of the item to be removed.

        Return value:
        True -- item has been removed
        False -- item could not be removed, either due to an empty service plan or
            an invalid index being specified
        """
        if index >= 0 and self.items and index < len(self.items):
            del self.items[index]
            self.modified = True
            if index == self.item_index:
                # Current item was removed
                if self.item_index > 0:
                    self.item_index -= 1
                    self.slide_index = 0
                elif not self.items:
                    self.item_index = -1
                    self.slide_index = -1
            elif index < self.item_index:
                self.item_index -= 1
                self.slide_index = 0
            self.autosave()
            return True
        else:
            return False
        
    def remove_song(self, s_id):
        """
        Removes all instances of a given song from the service
        """
        song_instances = []
        for idx, item in enumerate(self.items):
            if type(item).__name__ == "Song" and item.song_id == s_id:
                song_instances.append(idx)
        if song_instances:
            for idx in reversed(song_instances):
                self.remove_item_at(idx)
            return True
        else:
            return False

    def move_item(self, from_index, to_index):
        """
        Move an item to a different position in the service plan.

        Arguments:
        from_index -- the index of the item to move
        to_index -- the index to move the item to

        Return value:
        0 -- No need to move items as from_index == to_index
        1 -- Item successfully moved
        -1 -- Invalid index specified (either from_index or to_index)
        """
        if from_index == to_index or not self.items:
            return 0 # No need to move items

        if 0 <= from_index < len(self.items) and 0 <= to_index <= len(self.items):
            if from_index < to_index:
                self.items.insert(to_index + 1, self.items[from_index])
                del self.items[from_index]
            else:
                self.items.insert(to_index, self.items[from_index])
                del self.items[from_index + 1]
            self.modified = True
            self.autosave()
            return 1 # Item successfully moved
        
        return -1 # Invalid index specified

    def get_current_item_type(self):
        """Return the type of the currently selected item"""
        if self.item_index >= 0:
            return type(self.items[self.item_index]).__name__
        else:
            return None
        
    def get_item_type(self, index):
        """Return the type of a specified item, or None if invalid index given"""
        if index >= 0 and index < len(self.items):
            return type(self.items[index]).__name__
        else:
            return None

    def set_item_index(self, index):
        """
        Set which item is currently selected in the service plan.

        Keyword:
        index -- the index of the item to select

        Return value:
        True -- the specified index was selected
        False -- the specified index was invalid and could not be selected
        """
        if 0 <= index < len(self.items):
            self.item_index = index
            self.slide_index = 0 # Select the first slide of this item
            return True
        else:
            return False

    def next_item(self):
        """
        Advance to the next item in the service plan.

        Return value:
        True -- successfully advanced to next item in the service plan
        False -- could not advance to next item (service plan empty or at last item already)
        """
        if (self.item_index + 1) < len(self.items):
            self.item_index += 1
            self.slide_index = 0
            return True
        else:
            return False

    def previous_item(self):
        """
        Advance to the previous item in the service plan.

        Return value:
        True -- successfully advanced to previous item in the service plan
        False -- could not advance to previous item (service plan empty or at first item already)
        """
        if self.item_index > 0:
            self.item_index -= 1
            self.slide_index = 0
            return True
        else:
            return False

    def set_slide_index(self, index):
        """
        Set the current slide index in the current service item.

        Arguments:
        index -- the slide index to change to.

        Return value:
        1 -- successfully changed current slide index
        0 -- could not change to specified slide index as index is out of bounds
        -1 -- could not change to specified slide index as no item is selected in the service plan
        """
        if self.item_index < 0:
            return -1
        if index >= len(self.items[self.item_index].slides):
            return 0
        self.slide_index = index
        return 1

    def next_slide(self):
        """
        Advance to the next slide in the current service item.

        Return value:
        1 -- successfully advanced to next slide
        0 -- could not advance to next slide as at last slide already
        -1 -- could not advance to next slide as no item is selected in the service plan
        """
        if self.item_index < 0:
            return -1
        if (self.slide_index + 1) >= len(self.items[self.item_index].slides):
            return 0
        self.slide_index += 1
        return 1

    def previous_slide(self):
        """
        Advance to the previous slide in the current service item.

        Return value:
        1 -- successfully advanced to previous slide
        0 -- could not advance to previous slide as at first slide already
        -1 -- could not advance to previous slide as no item is selected in the service plan
        """
        if self.item_index < 0:
            return -1
        if self.slide_index == 0:
            return 0
        self.slide_index -= 1
        return 1

    def to_JSON_simple(self):
        """
        Return a JSON object containing the titles of all items in the current service plan,
        as well as the current item_index and slide_index.
        """
        return json.dumps({"items": [x.get_title() for x in self.items],
                           "item_index": self.item_index,
                           "slide_index": self.slide_index}, indent=2)

    def to_JSON_full(self):
        """
        Return a JSON object containing the JSON representation of all items in the current
        service plan, as well as the current item_index and slide_index.
        """
        return json.dumps({"filename": self.file_name,
                           "items": [json.loads(x.to_JSON(0)) for x in self.items],
                           "item_index": self.item_index,
                           "slide_index": self.slide_index}, indent=2)

    def to_JSON_titles_and_current(self, capo):
        """
        Return a JSON object containing the titles and types of all items in the current
        service plan, the JSON representation of the currently selected item ({} if no
        item selected), as well as the current item_index and slide_index.

        Arguments:
        capo -- the capo being used by the client requesting this information
        """
        all_items = [json.loads(x.to_JSON(0)) for x in self.items]
        type_list = []
        for item in all_items:
            if item["type"] == "song":
                type_list.append("song-" + str(item["song-id"]))
            else:
                type_list.append(item["type"])
        if self.item_index > -1 and self.items:
            return json.dumps({
                "filename": self.file_name,
                "items": [x.get_title() for x in self.items],
                "types": type_list,
                "current_item": json.loads(self.items[self.item_index].to_JSON(capo)),
                "item_index": self.item_index,
                "slide_index": self.slide_index}, indent=2)
        else:
            return json.dumps({
                "filename": self.file_name,
                "items": [x.get_title() for x in self.items],
                "types": type_list,
                "current_item": {},
                "item_index": self.item_index,
                "slide_index": self.slide_index}, indent=2)

    def load_service(self, fname, cur_style, bible_versions):
        """
        Load a saved service plan, paginating items according to the specified style.

        Arguments:
        fname -- the filename of the saved service within the ./services directory.
        cur_style -- the style to use when paginating service items.

        Possible exceptions:
        MalformedServiceFileError -- raised if the saved service does not have the correct structure
        InvalidServiceURLError -- raised if fname does not exist in the ./services directory
        MissingStyleParameterError - raised if one or more style parameters have not been specified.
        """
        # Precondition: fname is a JSON file in the folder ./services
        full_path = "./services/" + fname
        if not os.path.isfile(full_path):
            raise InvalidServiceUrlError(full_path)
        with open(full_path) as f:
            json_data = json.load(f)
        if "items" not in json_data:
            raise MalformedServiceFileError(full_path, "Missing key: 'items'")
        self.items = []
        self.file_name = fname
        for item in json_data["items"]:
            if not "type" in item:
                raise MalformedServiceFileError(full_path, "Missing key: 'type'")
            if item["type"] == "bible":
                if "version" in item and "start_id" in item and "end_id" in item:
                    try:
                        b = BiblePassage(item["version"], \
                            item["start_id"], item["end_id"], cur_style, bible_versions)
                        if "parallel_version" in item and item["parallel_version"] != "":
                            b.parallel_paginate_from_style(cur_style, item["parallel_version"], bible_versions)
                        self.add_item(b)
                    except MissingStyleParameterError as style_e:
                        raise MissingStyleParameterError(style_e.msg[42:]) from style_e
                else:
                    raise MalformedServiceFileError(full_path, "Missing key for Bible passage")
            elif item["type"] == "song":
                if "song_id" in item:
                    try:
                        s = Song(item["song_id"], cur_style)
                        self.add_item(s)
                    except MissingStyleParameterError as style_e:
                        raise MissingStyleParameterError(style_e.msg[42:]) from style_e
                else:
                    raise MalformedServiceFileError(full_path, "Missing key: 'song_id'")
            elif item["type"] == "video":
                if "url" in item:
                    v = Video(item["url"])
                    self.add_item(v)
                else:
                    raise MalformedServiceFileError(full_path, "Missing key: 'url'")
            elif item["type"] == "presentation":
                if "url" in item:
                    p = Presentation(item["url"])
                    self.add_item(p)
                else:
                    raise MalformedServiceFileError(full_path, "Missing key: 'url'")
        if len(self.items) > 0:
            self.item_index = 0
            self.slide_index = 0
        self.modified = False

    @classmethod
    def import_service(cls, zip_path, cur_style, bible_versions):
        """
        Import a zipped service plan, paginating items according to the specified style.

        Arguments:
        zip_path -- the full path of the zipped service, probably on external drive
        cur_style -- the style to use when paginating service items.

        Possible exceptions:
        MalformedServiceFileError -- raised if the saved service does not have the correct structure
        MissingStyleParameterError - raised if one or more style parameters have not been specified.
        """
        imported_service = Service()
        with ZipFile(zip_path, 'r') as z:
            if not 'manifest.json' in z.namelist():
                raise MalformedServiceFileError(zip_path, "Missing service manifest")
            try:
                json_data = json.loads(z.read('manifest.json').decode('utf-8'))
            except JSONDecodeError as _:
                raise MalformedServiceFileError(zip_path, "Service file couldn't be decoded")
        if "items" not in json_data:
            raise MalformedServiceFileError(zip_path, "Missing key: 'items'")
        imported_service.file_name = os.path.basename(zip_path)[:-4] + ".json"
        if os.path.exists('./services/' + imported_service.file_name):
            timestamp = datetime.now().strftime('_%Y%m%d_%H%M%S')
            imported_service.file_name = imported_service.file_name[:-5] + timestamp + ".json"
        for item in json_data["items"]:
            if not "type" in item:
                raise MalformedServiceFileError(zip_path, "Missing key: 'type'")
            if item["type"] == "bible":
                if "version" in item and "ref" in item:
                    try:
                        b = BiblePassage.import_from_JSON(item, cur_style, bible_versions)
                        imported_service.add_item(b)
                    except MissingStyleParameterError as style_e:
                        raise MissingStyleParameterError(style_e.msg[42:]) from style_e
                    except InvalidVersionError as inv_e:
                        raise InvalidVersionError(inv_e.msg[40:]) from inv_e
                    except MalformedReferenceError as mal_e:
                        raise MalformedReferenceError(mal_e.msg[50:]) from mal_e
                    except UnknownReferenceError as un_e:
                        raise UnknownReferenceError(un_e.msg[61:]) from un_e
                else:
                    raise MalformedServiceFileError(zip_path, "Missing key for Bible passage")
            elif item["type"] == "song":
                if "title" in item and "lyrics_chords" in item and "verse_order" in item:
                    try:
                        s = Song.import_from_JSON(item, zip_path, cur_style)
                        imported_service.add_item(s)
                    except MissingStyleParameterError as style_e:
                        raise MissingStyleParameterError(style_e.msg[42:]) from style_e
                else:
                    raise MalformedServiceFileError(zip_path, "Missing key(s) for Song")
            elif item["type"] == "video":
                if "url" in item:
                    v = Video.import_from_JSON(item, zip_path)
                    imported_service.add_item(v)
                else:
                    raise MalformedServiceFileError(zip_path, "Missing key: 'url'")
            elif item["type"] == "presentation":
                if "url" in item:
                    p = Presentation.import_from_JSON(item, zip_path)
                    imported_service.add_item(p)
                else:
                    raise MalformedServiceFileError(zip_path, "Missing key: 'url'")
        imported_service.save()

    def save(self):
        """
        Save the current service plan.

        Possible exceptions:
        UnspecifiedServiceUrl - raised if a save file has not previously been specified.
        """
        if self.file_name is None:
            raise UnspecifiedServiceUrl()
        with open("./services/" + self.file_name, 'w') as json_file:
            json.dump({"items": [json.loads(x.save_to_JSON()) for x in self.items]}, json_file)
        self.modified = False

    def save_as(self, fname):
        """
        Save the current service plan to the specified file.

        Arguments:
        fname -- the name of the save file within the ./services directory.
        """
        self.file_name = fname
        self.save()

    def autosave(self):
        """
        Autosave the current service plan to /services/autosave.json.
        """
        with open("./services/autosave.json", 'w') as json_file:
            json.dump({"items": [json.loads(x.save_to_JSON()) for x in self.items]}, json_file)

    def export_as(self, fname):
        """
        Exports the current service plan to the specified zip file, which can exist anywhere in the filesystem.

        Arguments:
        fname -- the name of the export zip file.
        """
        # x.export_to_JSON calls will add video and presentation resources to the zip file.
        if not fname.endswith('.zip'):
            fname += ".zip"
        exported_service = json.dumps(
            {"items": [json.loads(x.export_to_JSON(fname)) for x in self.items]}, indent=2)
        with ZipFile(fname, 'a') as out_zip:
            out_zip.writestr('manifest.json', exported_service)

    @classmethod
    def get_all_services(cls):
        """Return a list of all saved services within the ./services directory."""
        fnames = glob.glob('./services/*.json')
        fnames.sort(key=os.path.getmtime, reverse=True)
        return [os.path.basename(fname) for fname in fnames]

### TESTING ONLY ###
if __name__ == "__main__":
    pass
