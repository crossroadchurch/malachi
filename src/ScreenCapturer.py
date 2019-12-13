# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""
Produce screen captures for mirroring of presentations to clients using the /monitor websocket.
"""

import asyncio
import os
import threading
import time
import mss
from PIL import Image, ImageChops

# Basic stoppable thread code from:
# https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread

class ScreenCapturer(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, server, mon):
        super(ScreenCapturer, self).__init__()
        total_mons = len(mss.mss().monitors) - 1
        if mon > 0 and mon <= total_mons:
            self.mon = mon
        else:
            self.mon = 1
        self.mon_w = mss.mss().monitors[self.mon]["width"]
        self.mon_h = mss.mss().monitors[self.mon]["height"]
        self.mserver = server
        self._stop_event = threading.Event()

    def change_monitor(self, mon):
        """
        Change the monitor being used for capturing.  If an invalid monitor is chosen then
        no update is made and the function returns no error.

        Arguments:
        mon -- the index of monitor to capture from.  1 = primary display, 2 = extended display.
        """
        # mss.mss().monitors - index 0 is concatenated monitor, index N>0 is individual monitor
        total_mons = len(mss.mss().monitors) - 1
        if mon > 0 and mon <= total_mons:
            self.mon = mon
            self.mon_w = mss.mss().monitors[self.mon]["width"]
            self.mon_h = mss.mss().monitors[self.mon]["height"]

    def stop(self):
        """ Stop the capture thread."""
        self._stop_event.set()

    def stopped(self):
        """ Return the stopped state of the thread."""
        return self._stop_event.is_set()

    def run(self):
        """ Start the thread asynchronously."""
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._run())
        loop.close()

    def equal_images(self, i1, i2):
        """
        Test two images for pixel-by-pixel equality.

        Arguments:
        i1, i2 -- images to compare, of class PIL.Image

        Returns:
        True if and only if each pixel of i1 equals the corresponding pixel of i2, False otherwise.
        """
        if not i1.size == i2.size:
            return False
        return ImageChops.difference(i1, i2).getbbox() is None

    async def _run(self):
        """ Run the thread.  Take a new screen capture every 2 seconds."""
        out_num = 0
        prev_capture = Image.new('RGB', (100, 100))
        with mss.mss() as sct:
            while not self.stopped():
                capture_png = "./captures/capture_{n}.png".format(n=out_num)
                sct.shot(mon=self.mon, output=capture_png)
                time.sleep(0.25)
                cur_capture = Image.open(capture_png)
                if not self.equal_images(prev_capture, cur_capture):
                    # Only serve capture if it is different to the previous one served
                    capture_jpg = "./captures/capture_{n}.jpg".format(n=out_num)
                    im_out = Image.new("RGB", cur_capture.size, (255, 255, 255))
                    im_out.paste(cur_capture, (0, 0))
                    im_out.save(capture_jpg, quality=90)
                    time.sleep(0.25)
                    # Serve the smaller capture to clients
                    if os.path.getsize(capture_png) < os.path.getsize(capture_jpg):
                        await self.mserver.capture_update(capture_png, \
                            sct.monitors[self.mon]["width"], sct.monitors[self.mon]["height"])
                    else:
                        await self.mserver.capture_update(capture_jpg, \
                            sct.monitors[self.mon]["width"], sct.monitors[self.mon]["height"])
                    out_num = (out_num + 1) % 5
                    prev_capture = cur_capture
                    time.sleep(1.5)
                else:
                    time.sleep(1.75)
