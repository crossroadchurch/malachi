# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""
Produce screen captures for mirroring of presentations to clients using the /monitor websocket.
"""

import asyncio
import threading
import time
import mss

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
        """ Run the thread.  Take a new screen capture every 2 seconds."""
        out_num = 0
        with mss.mss() as sct:
            while not self.stopped():
                capture_url = "./captures/capture_{n}.png".format(n=out_num)
                sct.shot(mon=self.mon, output=capture_url)
                await self.mserver.capture_update(capture_url, \
                    sct.monitors[self.mon]["width"], sct.monitors[self.mon]["height"])
                out_num = (out_num + 1) % 5
                time.sleep(2)
