# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Represent a Background image in Malachi"""

import os
import math
import json
import re
import cv2
from MalachiExceptions import InvalidBackgroundUrlError

class Background():
    """Represent a Background image in Malachi"""

    def __init__(self, url):
        # URL is relative to Malachi directory, e.g. "./backgrounds/image.jpg"
        if not os.path.isfile(url):
            raise InvalidBackgroundUrlError(url)
        self.url = os.path.split(url)[0] + "/" + \
            re.sub(r'[^a-zA-Z0-9 \'\-_.,()]', '', os.path.split(url)[1])
        # Remove invalid characters from url, renaming source file as appropriate
        if self.url != url:
            os.rename(os.path.abspath(url), os.path.abspath(self.url))
        self.title = os.path.basename(self.url)
        img = cv2.imread(self.url)
        self.image_width = img.shape[1]
        self.image_height = img.shape[0]
        # Generate thumbnail if needed
        if not os.path.isfile('./backgrounds/thumbnails/' + self.title):
            scale_factor = 128 / self.image_width
            thumbnail = cv2.resize(img, (0, 0), fx=scale_factor, fy=scale_factor)
            cv2.imwrite('./backgrounds/thumbnails/' + self.title, thumbnail)

    def get_title(self):
        """Return the title of the Background"""
        return self.title

    # pylint: disable=W0613 # capo is unused due to OOP coding of to_JSON method
    def to_JSON(self, capo):
        """
        Return a JSON object containing all the data needed to display this background
        to a client.
        """
        return json.dumps({
            "type": "background",
            "title": self.title,
            "url": self.url,
            "image_height": self.image_height,
            "image_width": self.image_width}, indent=2)
    # pylint: enable=W0613

    def __str__(self):
        return self.get_title()

    @classmethod
    def get_all_backgrounds(cls):
        """Return a list of all background URLs in the ./backgrounds directory."""
        Background.generate_background_thumbnails()
        urls = ['./backgrounds/' + f for f in os.listdir('./backgrounds')
            if f.endswith('.jpg') or f.endswith('.JPG') or f.endswith('.png') or f.endswith('.PNG')]
        if urls:
            urls.sort()
        return urls

    @classmethod
    def generate_background_thumbnails(cls):
        """Ensure that all backgrounds have a corresponding thumbnail."""
        backgrounds = [f for f in os.listdir('./backgrounds')
            if f.endswith('.jpg') or f.endswith('.JPG') or f.endswith('.png') or f.endswith('.PNG')]
        for fname in backgrounds:
            if not os.path.isfile('./backgrounds/thumbnails/' + fname):
                Background('./backgrounds/' + fname)
