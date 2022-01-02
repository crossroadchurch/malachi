# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Run the Malachi song projection system"""

import asyncio
import time
import sys
import io
import os
import re
import requests
import websockets
from requests.exceptions import ConnectionError

# Add src directory to path to enable Malachi modules to be found
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"))

# pylint: disable=C0413
from src.MalachiServer import MalachiServer
from src.MalachiExceptions import MissingDataFilesError
from src.ThreadedHTTPServer import ThreadedHTTPServer
from src._version import __version__
# pylint: enable=C0413

# https://raspberrypi.stackexchange.com/questions/5100/detect-that-a-python-program-is-running-on-the-pi
def is_raspberrypi():
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower(): return True
    except Exception: pass
    return False


if __name__ == "__main__":

    # Check for updates to Malachi
    try:
        repo_page = requests.get('https://github.com/crossroadchurch/malachi/commits/master')
        if repo_page.status_code == 200:
            latest_sha = re.findall('malachi/commit/[0-9a-f]*', repo_page.text)[0][15:]
            old_sha = 0
            if os.path.isfile('sha.txt'):
                with open('sha.txt', 'r') as old_sha_file:
                    old_sha = old_sha_file.read()
            if old_sha != latest_sha:
                if sys.platform == 'win32':
                    print("********************************************************")
                    print("*          An update for Malachi is available.         *")
                    print("*  You can install it by running \'Update Malachi.bat\'  *")
                    print("********************************************************")
                    print()
                elif sys.platform == 'linux':
                    if is_raspberrypi():
                        print("********************************************************")
                        print("*          An update for Malachi is available.         *")
                        print("*  You can install it by running \'update_malachi_pi\'   *")
                        print("********************************************************")
                        print()
                    else:
                        print("**********************************************************")
                        print("*           An update for Malachi is available.          *")
                        print("*  You can install it by running \'update_malachi_linux\'  *")
                        print("**********************************************************")
                        print()

    except ConnectionError as e:
        pass
    
    print("Welcome to Malachi v{v}".format(v=__version__))
    # Start web server
    HTTP_SERVER = ThreadedHTTPServer('0.0.0.0', 8000)
    HTTP_SERVER.start()
    time.sleep(2)

    try:
        MALACHI_SERVER = MalachiServer()

        # Start websocket server
        asyncio.get_event_loop().run_until_complete(
            websockets.serve(MALACHI_SERVER.responder, '0.0.0.0', 9001)
        )
        asyncio.get_event_loop().run_forever()
        HTTP_SERVER.stop()

    except MissingDataFilesError as crit_error:
        print("Critical error, stopping Malachi")
