import sys, signal
import http.server
import socketserver
import threading

class ThreadedHTTPServer(object):
    def __init__(self, host, port):
        handler = http.server.SimpleHTTPRequestHandler
        self.server = socketserver.ThreadingTCPServer((host, port), handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True

    def start(self):
        self.server_thread.start()
        print("Server started successfully")

    def stop(self):
        self.server.server_close()
        print("Server stopped successfully")