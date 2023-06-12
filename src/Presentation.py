# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Represent a Presentation object in Malachi"""

import os
import json
import binascii
from datetime import datetime
from zipfile import ZipFile
from MalachiExceptions import InvalidPresentationUrlError

class Presentation():
    """Represent a Presentation object in Malachi"""

    def __init__(self, url):
        # URL is relative to Malachi directory, e.g. "./presentations/presentation.ppt"
        if not os.path.isfile(url):
            raise InvalidPresentationUrlError(url)
        self.url = url
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

    def export_to_JSON(self, export_zip):
        """
        Return a JSON object representing this Presentation for exporting to another
        instance of Malachi and add the presentation to export_zip.
        """
        with ZipFile(export_zip, 'a') as out_zip:
            # Test if Presentation has already been written to out_zip
            if self.url[2:] not in out_zip.namelist():
                out_zip.write(self.url)
        return json.dumps({
            "type": "presentation",
            "url": self.url
        })

    @classmethod
    def import_from_JSON(cls, json_data, export_zip):
        """
        Return a Presentation object corresponding to the presentation stored in json_data,
        which has been exported (possibly from another instance of Malachi) using the
        export_to_JSON method.  The presentation is extracted from export_zip if it doesn't
        already exist in ./presentations.

        Precondition: json_data["type"] == "presentation"
        Precondition: json_data["url"][2:] exists in export_zip
        """
        url = json_data["url"]
        # Extract url from export_zip if it doesn't exist in ./presentations
        with ZipFile(export_zip, 'a') as out_zip: # mode must be 'a' in case we need to modify filename in zip
            if not os.path.exists(url):
                out_zip.extract(url[2:])
            else:
                # A presentation at url exists.  Use CRC32 to test if it is the same
                # as the one stored in out_zip
                idx = [index for index, element in enumerate(out_zip.infolist()) 
                    if element.filename == url[2:]][0]
                crc_zip = out_zip.infolist()[idx].CRC
                disk_pres = open(url, 'rb').read()
                crc_disk = binascii.crc32(disk_pres)
                if crc_zip != crc_disk:
                    # Presentation on disk is different to one stored in zip file.
                    # Append timestamp to presentation in zip file before extracting and
                    #  update url used in Malachi accordingly
                    path_parts = os.path.splitext(url)
                    url = path_parts[0] + datetime.now().strftime('_%Y%m%d_%H%M%S') + path_parts[1]
                    out_zip.infolist()[idx].filename = url[2:]
                    out_zip.extract(out_zip.infolist()[idx])

        # Create Presentation object
        return Presentation(url)


    @classmethod
    def get_all_presentations(cls):
        """Return a list of all presentation URLs in the ./presentations directory."""
        urls = ['./presentations/' + f for f in os.listdir('./presentations')
                if f.endswith('.ppt') or f.endswith('pptx') or f.endswith('odp') or f.endswith('ppsx')]
        if urls:
            urls.sort()
        return urls

### TESTING ONLY ###
if __name__ == "__main__":
    pass
