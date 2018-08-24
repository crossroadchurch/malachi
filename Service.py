import json, requests
from BiblePassage import BiblePassage
from Song import Song, InvalidSongIdError
from Presentation import Presentation, InvalidPresentationUrlError

class Service():

    def __init__(self):
        self.items = []
        self.item_index = -1
        self.slide_index = -1

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

    def load_service(self, url):
        # Precondition: url is a JSON file
        # TODO: Exception catching and handling
        result = requests.get(url)
        json_data = result.json()
        self.items = []
        for item in json_data["items"]:
            if item["type"] == "bible":
                self.add_item(BiblePassage(item["version"], item["start_id"], item["end_id"]))
            elif item["type"] == "song":
                self.add_item(Song(item["song_id"]))
            elif item["type"] == "presentation":
                self.add_item(Presentation(item["url"]))

    def save_to_JSON(self):
        json_items = json.dumps({"items": [json.loads(x.save_to_JSON()) for x in self.items]}, indent=2)
        return json_items

### TESTING ONLY ###
if __name__ == "__main__":
    pass