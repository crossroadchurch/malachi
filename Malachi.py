# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Run the Malachi song projection system"""

import asyncio
import time
import sys
import os
import websockets

# Add src directory to path to enable Malachi modules to be found
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"))

# pylint: disable=C0413
from src.MalachiServer import MalachiServer
from src.MalachiExceptions import MissingDataFilesError
from src.ThreadedHTTPServer import ThreadedHTTPServer
# pylint: enable=C0413

if __name__ == "__main__":
    # Start web server
    HTTP_SERVER = ThreadedHTTPServer('0.0.0.0', 8000)
    HTTP_SERVER.start()
    time.sleep(2)

    # In Linux need to run:
    # soffice --accept="socket,host=localhost,port=2002;urp" --quickstart
    # in a separate terminal before starting Malachi

    try:
        MALACHI_SERVER = MalachiServer()
        MALACHI_SERVER.s.load_service('service_test.json',\
            MALACHI_SERVER.style_list[MALACHI_SERVER.current_style],\
            MALACHI_SERVER.bible_versions)
        MALACHI_SERVER.s.set_item_index(0)

        # Start websocket server
        asyncio.get_event_loop().run_until_complete(
            websockets.serve(MALACHI_SERVER.responder, '0.0.0.0', 9001)
        )
        asyncio.get_event_loop().run_forever()
        HTTP_SERVER.stop()

    except MissingDataFilesError as crit_error:
        print("Critical error, stopping Malachi")
