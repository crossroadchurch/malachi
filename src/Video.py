# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Represent a Video object in Malachi"""

import os
import math
import json
import cv2
from MalachiExceptions import InvalidVideoUrlError

class Video():
    """Represent a Video object in Malachi"""

    def __init__(self, url):
        # URL is relative to Malachi directory, e.g. "./videos/video.mp4"
        if os.path.isfile(url):
            self.url = url
        else:
            raise InvalidVideoUrlError(url)
        self.title = os.path.basename(url)
        vid = cv2.VideoCapture(url)
        self.fps = vid.get(cv2.CAP_PROP_FPS)
        frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = math.floor(frames/self.fps)
        mins, secs = divmod(self.duration, 60)
        self.slides = ["Video: " + self.title + "\nDuration: {}:{:02}".format(mins, secs)]

    def get_title(self):
        """Return the title of the Video"""
        return self.title

    def get_duration(self):
        """Return the duration of the Video in seconds"""
        return self.duration

    # pylint: disable=W0613 # capo is unused due to OOP coding of to_JSON method
    def to_JSON(self, capo):
        """
        Return a JSON object containing all the data needed to display this video
        to a client.
        """
        return json.dumps({
            "type":"video",
            "title":self.title,
            "slides":self.slides,
            "duration": self.duration}, indent=2)
    # pylint: enable=W0613

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        """Return a JSON object representing this Video for saving in a service plan."""
        return json.dumps({"type": "video", "url": self.url})

    @classmethod
    def get_all_videos(cls):
        """Return a list of all video URLs in the ./videos directory."""
        urls = ['./videos/' + f for f in os.listdir('./videos')
                if f.endswith('.mpg') or f.endswith('mp4')]
        return urls

### TESTING ONLY ###
if __name__ == "__main__":
    pass
