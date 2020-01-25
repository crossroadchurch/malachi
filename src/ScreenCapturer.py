# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""
Produce screen captures for mirroring of presentations to clients using the /monitor websocket.
"""

import asyncio
import base64
from io import BytesIO
import threading
import mss
from PIL import Image

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

    async def _run(self):
        """ Run the thread.  Take a new screen capture every second."""
        prev_png_bytes = b""
        with mss.mss() as sct:
            while not self.stopped():
                sct_img = sct.grab(sct.monitors[self.mon])
                new_frame = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img_buffer = BytesIO()
                new_frame.save(img_buffer, format="PNG")
                png_bytes = base64.b64encode(img_buffer.getvalue())
                if not png_bytes == prev_png_bytes:
                    # Only serve image if it is different to the previous one served
                    img_buffer = BytesIO()
                    new_frame.save(img_buffer, format="JPEG", quality=90)
                    jpg_bytes = base64.b64encode(img_buffer.getvalue())
                    if len(png_bytes) <= len(jpg_bytes):
                        await self.mserver.capture_ready(\
                            "data:image/png;base64," + png_bytes.decode('utf-8'))
                    else:
                        await self.mserver.capture_ready(\
                            "data:image/jpeg;base64," + png_bytes.decode('utf-8'))
                    prev_png_bytes = png_bytes
                await asyncio.sleep(self.mserver.capture_refresh_rate/1000)
