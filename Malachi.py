import asyncio, websockets, time
from src.MalachiServer import MalachiServer
from src.ThreadedHTTPServer import ThreadedHTTPServer

if __name__ == "__main__":  
    # Start web server
    server = ThreadedHTTPServer('0.0.0.0', 8000)
    server.start()

    # In Linux need to run soffice --accept="socket,host=localhost,port=2002;urp" --quickstart in a separate terminal before starting Malachi

    time.sleep(2)

    m = MalachiServer()
    m.s.load_service('service_test.json', m.style_list[m.current_style])
    m.s.set_item_index(0)

    # Start websocket server
    asyncio.get_event_loop().run_until_complete(
        websockets.serve(m.responder, '0.0.0.0', 9001)
    )
    asyncio.get_event_loop().run_forever()
    server.stop()