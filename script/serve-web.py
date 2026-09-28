"""Serves the built site with the headers the wasm threads need."""

import functools
import http.server
import socketserver


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    import sys

    port = int(sys.argv[1])
    root = sys.argv[2]
    handler = functools.partial(Handler, directory=root)
    with Server(("127.0.0.1", port), handler) as httpd:
        httpd.serve_forever()
