# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Start the Malachi app and screen windows (Windows OS only)"""

import os
import ctypes
import subprocess
import warnings
from pywinauto import Application, ElementNotFoundError, mouse

warnings.simplefilter('ignore', category=UserWarning)

OLD_CHROME_PATH = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
NEW_CHROME_PATH = "C:/Program Files/Google/Chrome/Application/chrome.exe"

if os.path.isfile(OLD_CHROME_PATH):
    chrome_path = OLD_CHROME_PATH
elif os.path.isfile(NEW_CHROME_PATH):
    chrome_path = NEW_CHROME_PATH
else:
    print("Couldn't find Google Chrome installed in Program Files")
    exit()

user32 = ctypes.windll.user32
# Compare primary screen width to virtual screen width to determine if using multiple monitors
if user32.GetSystemMetrics(0) == user32.GetSystemMetrics(78):
    print("Single screen detected - only opening Malachi App")
    subprocess.Popen([chrome_path, "http://localhost:8000/app", "--new-window"])
    app_loaded = False
    while not app_loaded:
        try:
            app = Application(backend="win32").connect(
                title="Malachi App - Google Chrome")
            app_loaded = True
        except ElementNotFoundError as e:
            pass
    app_window = app.window(title="Malachi App - Google Chrome")
    app_window.move_window(x=0, y=0, width=1366, height=768)
    # Restore and then maximise app window
    app_window.type_keys("%{VK_SPACE}")
    app_window.type_keys('R')
    app_window.type_keys("%{VK_SPACE}")
    app_window.type_keys('X')
else:
    print("Multiple screens detected - opening Malachi App and Malachi Screen")
    subprocess.Popen([chrome_path, "http://localhost:8000/app", "--new-window"])
    subprocess.Popen([chrome_path, "http://localhost:8000/screen", "--new-window"])
    app_loaded = False
    while not app_loaded:
        try:
            app = Application(backend="win32").connect(
                title="Malachi App - Google Chrome")
            app_loaded = True
        except ElementNotFoundError as e:
            pass
    app_window = app.window(title="Malachi App - Google Chrome")
    app_window.move_window(x=0, y=0, width=1366, height=768)
    screen_loaded = False
    while not screen_loaded:
        try:
            screen = Application(backend="win32").connect(
                title="Malachi Screen - Google Chrome")
            screen_loaded = True
        except ElementNotFoundError as e:
            pass
    screen_window = screen.window(title="Malachi Screen - Google Chrome")
    screen_window.move_window(x=2000, y=0, width=600, height=400)
    screen_window.set_focus()
    screen_window.type_keys("{F11}")
    mouse.click(button='left', coords=(2000,500))
    mouse.move(coords=(400,400))
    # Restore and then maximise app window
    app_window.type_keys("%{VK_SPACE}")
    app_window.type_keys('R')
    app_window.type_keys("%{VK_SPACE}")
    app_window.type_keys('X')