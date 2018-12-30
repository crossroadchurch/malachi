# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Provide a threaded HTTP server with support for custom routes."""

import os
import http.server
from http import HTTPStatus
import socketserver
import threading
import urllib.parse

class RoutedRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Provide a HTTP request handler with support for custom routes"""

    # Overriding method from http.server.SimpleHTTPRequestHandler to allow for custom routes
    def send_head(self):
        path = self.translate_path(self.path)
        f = None
        parts = urllib.parse.urlsplit(self.path)
        if os.path.isdir(path):
            if not parts.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(HTTPStatus.MOVED_PERMANENTLY)
                new_parts = (parts[0], parts[1], parts[2] + '/',
                             parts[3], parts[4])
                new_url = urllib.parse.urlunsplit(new_parts)
                self.send_header("Location", new_url)
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        # Custom routing
        if parts[2] in ["/music", "/music-control", "/singers", "/lighting", "/test"]:
            keep_len = len(path) - len(parts[2])
            path = path[:keep_len] + "/html/" + path[keep_len+1:] + ".html"
        # End custom routing
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return None
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs[6]))
            self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise


class ThreadedHTTPServer():
    """Provide a HTTP server in a separate thread to the main thread"""

    def __init__(self, host, port):
        handler = RoutedRequestHandler
        self.server = socketserver.ThreadingTCPServer((host, port), handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True

    def start(self):
        "Start the threaded server"
        self.server_thread.start()
        print("Server started successfully")

    def stop(self):
        "Stop the threaded server"
        self.server.server_close()
        print("Server stopped successfully")
