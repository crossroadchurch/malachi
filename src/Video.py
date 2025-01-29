# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Represent a Video object in Malachi"""

import os
import math
import json
import re
import cv2
import binascii
from datetime import datetime
from zipfile import ZipFile
from MalachiExceptions import InvalidVideoUrlError, InvalidVideoError

class Video():
    """Represent a Video object in Malachi"""

    def __init__(self, url):
        # URL is relative to Malachi directory, e.g. "./videos/video.mp4"
        if not os.path.isfile(url):
            raise InvalidVideoUrlError(url)
        self.url = os.path.split(url)[0] + "/" + \
            re.sub(r'[^a-zA-Z0-9 \-_.,()]', '', os.path.split(url)[1])
        # Remove invalid characters from url, renaming source file as appropriate
        if self.url != url:
            os.rename(os.path.abspath(url), os.path.abspath(self.url))
        self.title = os.path.basename(self.url)
        vid = cv2.VideoCapture(self.url)
        self.fps = vid.get(cv2.CAP_PROP_FPS)
        if self.fps == 0:
            raise InvalidVideoError(url)
        frames = int(vid.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = math.floor(frames/self.fps)
        mins, secs = divmod(self.duration, 60)
        self.slides = ["Video: " + self.title + "\nDuration: {}:{:02}".format(mins, secs)]
        self.video_width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # Generate thumbnail if needed
        if not os.path.isfile(self.url + ".jpg") or not os.path.isfile(self.url + "_still.jpg"):
            cv2_vid = cv2.VideoCapture(self.url)
            scale_factor = 128 / self.video_width
            still_factor = 1280 / self.video_width
            if self.duration > 10:
                cv2_vid.set(cv2.CAP_PROP_POS_FRAMES, 10*self.fps)
            else:
                cv2_vid.set(cv2.CAP_PROP_POS_FRAMES, 0)
            status, frame = cv2_vid.read()
            if status:
                thumbnail = cv2.resize(frame, (0, 0), fx=scale_factor, fy=scale_factor)
                cv2.imwrite(self.url + ".jpg", thumbnail)
                still_image = cv2.resize(frame, (0, 0), fx=still_factor, fy=still_factor)
                cv2.imwrite(self.url + "_still.jpg", still_image)

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

    def export_to_JSON(self, export_zip):
        """
        Return a JSON object representing this Video for exporting to another
        instance of Malachi and add the video to export_zip.
        """
        with ZipFile(export_zip, 'a') as out_zip:
            # Test if Video has already been written to out_zip
            if self.url[2:] not in out_zip.namelist():
                out_zip.write(self.url)
        return json.dumps({
            "type": "video",
            "url": self.url
        })

    @classmethod
    def import_from_JSON(cls, json_data, export_zip):
        """
        Return a Video object corresponding to the video stored in json_data,
        which has been exported (possibly from another instance of Malachi) using the
        export_to_JSON method.  The video is extracted from export_zip if it doesn't
        already exist in ./videos.

        Precondition: json_data["type"] == "video"
        Precondition: json_data["url"][2:] exists in export_zip
        """
        url = json_data["url"]
        # Extract url from export_zip if it doesn't exist in ./videos
        with ZipFile(export_zip, 'a') as out_zip: # mode must be 'a' in case we need to modify filename in zip
            if not os.path.exists(url):
                out_zip.extract(url[2:])
            else:
                # A video at url exists.  Use CRC32 to test if it is the same
                # as the one stored in out_zip
                idx = [index for index, element in enumerate(out_zip.infolist()) 
                    if element.filename == url[2:]][0]
                crc_zip = out_zip.infolist()[idx].CRC
                disk_pres = open(url, 'rb').read()
                crc_disk = binascii.crc32(disk_pres)
                if crc_zip != crc_disk:
                    # Video on disk is different to one stored in zip file.
                    # Append timestamp to video in zip file before extracting and
                    #  update url used in Malachi accordingly
                    path_parts = os.path.splitext(url)
                    url = path_parts[0] + datetime.now().strftime('_%Y%m%d_%H%M%S') + path_parts[1]
                    out_zip.infolist()[idx].filename = url[2:]
                    out_zip.extract(out_zip.infolist()[idx])

        # Create Video object
        return Video(url)

    @classmethod
    def get_all_videos(cls):
        """Return a list of all video URLs in the ./videos directory."""
        Video.generate_video_thumbnails()
        urls = ['./videos/' + f for f in os.listdir('./videos')
                if f.endswith('.mpg') or f.endswith('mp4') or f.endswith('mov')]
        if urls:
            urls.sort()
        return urls

    @classmethod
    def generate_video_thumbnails(cls):
        """Ensure that all videos and loops have a corresponding thumbnail."""
        loops = ['./loops/' + f for f in os.listdir('./loops')
                 if f.endswith('.mpg') or f.endswith('.mp4') or f.endswith('.mov')]
        videos = ['./videos/' + f for f in os.listdir('./videos')
                  if f.endswith('.mpg') or f.endswith('.mp4') or f.endswith('.mov')]
        for url in loops + videos:
            if not os.path.isfile(url + ".jpg") or not os.path.isfile(url + "_still.jpg"):
                try:
                    Video(url)
                except InvalidVideoError as e:
                    print(e.msg)
                    pass # Fail gracefully by ignoring video

### TESTING ONLY ###
if __name__ == "__main__":
    pass
