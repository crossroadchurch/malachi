# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Run the Malachi song projection system"""

import asyncio
import logging
import time
import sys
import os
import websockets
from datetime import datetime

# Add src directory to path to enable Malachi modules to be found
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"))

# pylint: disable=C0413
from src.MalachiServer import MalachiServer
from src.MalachiExceptions import MissingDataFilesError
from src.ThreadedHTTPServer import ThreadedHTTPServer
from src.StreamToLogger import StreamToLogger
from src._version import __version__
# pylint: enable=C0413

def main():
    # Setup logging of terminal output
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
        filename='./logs/' + datetime.now().strftime("%Y%m%d_%H%M%S") + '.log',
        filemode='a'
        )
    log = logging.getLogger('malachi')
    logging.raiseExceptions = False;
    sys.stdout = StreamToLogger(log,logging.INFO)
    sys.stderr = StreamToLogger(log,logging.ERROR)

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

    except MissingDataFilesError as _:
        print("Critical error, stopping Malachi")

if __name__ == "__main__":
    main()