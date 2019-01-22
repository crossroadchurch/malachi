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
        self.video_width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # Generate thumbnail if needed
        if not os.path.isfile(url + ".jpg"):
            cv2_vid = cv2.VideoCapture(url)
            scale_factor = 128 / self.video_width
            if self.duration > 10:
                cv2_vid.set(cv2.CAP_PROP_POS_FRAMES, 10*self.fps)
            else:
                cv2_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            status, frame = cv2_vid.read()
            if status:
                thumbnail = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
                cv2.imwrite(url + ".jpg", thumbnail)

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
            "type": "video",
            "title": self.title,
            "url": self.url,
            "slides": self.slides,
            "duration": self.duration,
            "video_height": self.video_height,
            "video_width": self.video_width}, indent=2)
    # pylint: enable=W0613

    def __str__(self):
        return self.get_title()

    def save_to_JSON(self):
        """Return a JSON object representing this Video for saving in a service plan."""
        return json.dumps({"type": "video", "url": self.url})

    @classmethod
    def get_all_videos(cls):
        """Return a list of all video URLs in the ./videos directory."""
        Video.generate_video_thumbnails()
        urls = ['./videos/' + f for f in os.listdir('./videos')
                if f.endswith('.mpg') or f.endswith('mp4') or f.endswith('mov')]
        return urls

    @classmethod
    def generate_video_thumbnails(cls):
        """Ensure that all videos and loops have a corresponding thumbnail."""
        loops = ['./loops/' + f for f in os.listdir('./loops')
                 if f.endswith('.mpg') or f.endswith('mp4') or f.endswith('mov')]
        videos = ['./videos/' + f for f in os.listdir('./videos')
                  if f.endswith('.mpg') or f.endswith('mp4') or f.endswith('mov')]
        for url in loops + videos:
            if not os.path.isfile(url + ".jpg"):
                Video(url)

### TESTING ONLY ###
if __name__ == "__main__":
    pass
