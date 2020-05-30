# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Start the Malachi app and screen windows (Windows OS only)"""

import time
import subprocess
import warnings
from pywinauto import Application

warnings.simplefilter('ignore', category=UserWarning)

subprocess.Popen(["firefox", "-new-window", "http://localhost:8000/app"])
subprocess.Popen(["firefox", "-new-window", "http://localhost:8000/screen"])
time.sleep(10)  # This may need to be increased if running on a slower system
app = Application(backend="win32").connect(
    title="Malachi App - Mozilla Firefox")
app_window = app.window(title="Malachi App - Mozilla Firefox")
app_window.move_window(x=0, y=0, width=1366, height=768)
screen = Application(backend="win32").connect(
    title="Malachi Screen - Mozilla Firefox")
screen_window = screen.window(title="Malachi Screen - Mozilla Firefox")
screen_window.move_window(x=2000, y=0, width=400, height=400)
screen_window.set_focus()
screen_window.type_keys("{F11}")
