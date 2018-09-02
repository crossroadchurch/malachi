import os, json, requests
from BiblePassage import BiblePassage
from Song import Song
from Presentation import Presentation
from MalachiExceptions import InvalidPresentationUrlError, InvalidServiceUrlError, InvalidSongIdError, MalformedServiceFileError, UnspecifiedServiceUrl

class Service():

    def __init__(self):
        self.items = []
        self.item_index = -1
        self.slide_index = -1
        self.file_name = None

    def add_item(self, item):
        self.items.append(item)

    def remove_item_at(self, index):
        if index >=0 and len(self.items)>0 and index < len(self.items):
            del self.items[index]

    def move_item(self, from_index, to_index):
        if from_index == to_index or len(self.items)==0:
            return # No need to move items
        else:
            if from_index < len(self.items) and to_index < len(self.items):
                if from_index < to_index:
                    self.items.insert(to_index, self.items[from_index])
                    del self.items[from_index]
                else:
                    self.items.insert(to_index, self.items[from_index])
                    del self.items[from_index + 1]
            else:
                return # Invalid index specified

    def get_current_item_type(self):
        if self.item_index >= 0:
            return type(self.items[self.item_index]).__name__

    def set_item_index(self, index):
        if index >= 0 and index < len(self.items):
            self.item_index = index
            self.slide_index = 0 # Select the first slide of this item (should this be -1 instead?)
            return True
        else:
            return False

    def next_item(self):
        if (self.item_index + 1) < len(self.items):
            self.item_index += 1
            self.slide_index = 0 # Or should this be -1?
            return True
        else:
            return False
    
    def previous_item(self):
        if self.item_index > 0:
            self.item_index -= 1
            self.slide_index = 0 # Or should this be -1?
            return True
        else:
            return False

    def set_slide_index(self, index):
        if self.item_index >= 0:
            if index >= 0 and index < len(self.items[self.item_index].slides):
                self.slide_index = index
                return True
            else:
                return False
        else:
            return False

    def next_slide(self):
        if self.item_index >= 0:
            if (self.slide_index + 1) < len(self.items[self.item_index].slides):
                self.slide_index += 1
                return True
            else:
                return False
        else:
            return False

    def previous_slide(self):
        if self.item_index >= 0 and self.slide_index > 0:
            self.slide_index -= 1
            return True
        else:
            return False

    def to_JSON_simple(self):
        return json.dumps({"items": [x.get_title() for x in self.items], 
                           "item_index": self.item_index,
                           "slide_index": self.slide_index}, indent=2)

    def to_JSON_full(self):
        return json.dumps({"items": [json.loads(x.to_JSON(0)) for x in self.items],
                           "item_index": self.item_index,
                           "slide_index": self.slide_index}, indent=2)

    def to_JSON_titles_and_current(self, capo):
        if self.item_index > -1 and len(self.items) > 0:
            return json.dumps({"items": [x.get_title() for x in self.items],
                            "current_item": json.loads(self.items[self.item_index].to_JSON(capo)),
                            "item_index": self.item_index,
                            "slide_index": self.slide_index}, indent=2)
        else:
            return json.dumps({"items": [x.get_title() for x in self.items],
                            "current_item": {},
                            "item_index": self.item_index,
                            "slide_index": self.slide_index}, indent=2)

    def load_service(self, fname):
        # Precondition: fname is a JSON file in the folder ./services
        if os.path.isfile("./services/" + fname):
            with open("./services/" + fname) as f:
                json_data = json.load(f)
            if "items" not in json_data:
                raise MalformedServiceFileError("./services/" + fname, "Missing key: 'items'")
            self.items = []
            self.file_name = fname
            for item in json_data["items"]:
                if "type" in item:
                    if item["type"] == "bible":
                        if "version" in item and "start_id" in item and "end_id" in item:
                            self.add_item(BiblePassage(item["version"], item["start_id"], item["end_id"]))
                        else:
                            raise MalformedServiceFileError("./services/" + fname, "Missing key for Bible passage")
                    elif item["type"] == "song":
                        if "song_id" in item:
                            self.add_item(Song(item["song_id"]))
                        else:
                            raise MalformedServiceFileError("./services/" + fname, "Missing key: 'song_id'")
                    elif item["type"] == "presentation":
                        if "url" in item:
                            self.add_item(Presentation(item["url"]))
                        else:
                            raise MalformedServiceFileError("./services/" + fname, "Missing key: 'url'")
                else:
                    raise MalformedServiceFileError("./services/" + fname, "Missing key: 'type'")
        else:
            raise InvalidServiceUrlError("./services/" + fname)
        

    def save(self):
        if self.file_name == None:
            raise UnspecifiedServiceUrl()
        else:
            with open("./services/" + self.file_name, 'w') as json_file:
                json.dump({"items": [json.loads(x.save_to_JSON()) for x in self.items]}, json_file)

    def save_as(self, fname):
        self.file_name = fname
        self.save()

    def save_to_JSON(self):
        json_items = json.dumps({"items": [json.loads(x.save_to_JSON()) for x in self.items]}, indent=2)
        return json_items

    @classmethod
    def get_all_services(cls):
        fnames = [f for f in os.listdir('./services') if f.endswith('.json')]
        return fnames

### TESTING ONLY ###
if __name__ == "__main__":
    pass