# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Start the Malachi app and screen windows (Windows OS only)"""

import time
import ctypes
import subprocess
import warnings
from pywinauto import Application

warnings.simplefilter('ignore', category=UserWarning)

user32 = ctypes.windll.user32
# Compare primary screen width to virtual screen width to determine if using multiple monitors
if user32.GetSystemMetrics(0) == user32.GetSystemMetrics(78):
    print("Single screen detected - only opening Malachi App")
    subprocess.Popen(["C:/Program Files (x86)/Google/Chrome/Application/chrome.exe", "http://localhost:8000/app", "--new-window"])
    time.sleep(10)  # This may need to be increased if running on a slower system
    app = Application(backend="win32").connect(
        title="Malachi App - Google Chrome")
    app_window = app.window(title="Malachi App - Google Chrome")
    app_window.move_window(x=0, y=0, width=1366, height=768)
else:
    print("Multiple screens detected - opening Malachi App and Malachi Screen")
    subprocess.Popen(["C:/Program Files (x86)/Google/Chrome/Application/chrome.exe", "http://localhost:8000/app", "--new-window"])
    subprocess.Popen(["C:/Program Files (x86)/Google/Chrome/Application/chrome.exe", "http://localhost:8000/screen", "--new-window"])
    time.sleep(10)  # This may need to be increased if running on a slower system
    app = Application(backend="win32").connect(
        title="Malachi App - Google Chrome")
    app_window = app.window(title="Malachi App - Google Chrome")
    app_window.move_window(x=0, y=0, width=1366, height=768)
    screen = Application(backend="win32").connect(
        title="Malachi Screen - Google Chrome")
    screen_window = screen.window(title="Malachi Screen - Google Chrome")
    screen_window.move_window(x=2000, y=0, width=600, height=400)
    screen_window.set_focus()
    screen_window.type_keys("{F11}")
