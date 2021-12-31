# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Represent a Presentation object in Malachi"""

import os
import json
from MalachiExceptions import InvalidPresentationUrlError

class Presentation():
    """Represent a Presentation object in Malachi"""

    def __init__(self, url):
        # URL is relative to Malachi directory, e.g. "./presentations/presentation.ppt"
        if os.path.isfile(url):
            self.url = url
        else:
            raise InvalidPresentationUrlError(url)
        self.title = os.path.basename(self.url)
        self.slides = ["Presentation: " + self.title]

    def get_title(self):
        """Return the title of the Presentation"""
        return self.title

    def get_url(self):
        """Return the URL of the Presentation"""
        return self.url

    # pylint: disable=W0613 # capo is unused due to OOP coding of to_JSON method
    def to_JSON(self, capo):
        """
        Return a JSON object containing all the data needed to display this presentation
        to a client.
        """
        return json.dumps({
            "type": "presentation",
            "title": self.title,
            "url": self.url,
            "slides": self.slides}, indent=2)
    # pylint: enable=W0613

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        """Return a JSON object representing this Presentation for saving in a service plan."""
        return json.dumps({"type": "presentation", "url": self.url})

    @classmethod
    def get_all_presentations(cls):
        """Return a list of all presentation URLs in the ./presentations directory."""
        urls = ['./presentations/' + f for f in os.listdir('./presentations')
                if f.endswith('.ppt') or f.endswith('pptx') or f.endswith('odp')]
        if urls:
            urls.sort()
        return urls

### TESTING ONLY ###
if __name__ == "__main__":
    pass
