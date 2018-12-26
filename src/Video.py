import os, math, json
import cv2
from .MalachiExceptions import InvalidVideoUrlError

class Video():

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
        self.slides = [ "Video: " + self.title + "\nDuration: {}:{:02}".format(mins,secs)]

    def get_title(self):
        return self.title

    def get_duration(self):
        return self.duration

    def to_JSON(self, capo):
        return json.dumps({"type":"video", "title":self.title, "slides":self.slides, "duration": self.duration}, indent=2)
    
    def __str__(self):
        return self.get_title()
    
    def save_to_JSON(self):
        return json.dumps({"type": "video", "url": self.url})

    @classmethod
    def get_all_videos(cls):
        urls = ['./videos/' + f for f in os.listdir('./videos')
                if f.endswith('.mpg') or f.endswith('mp4')]
        return urls

### TESTING ONLY ###
if __name__ == "__main__":
    pass