"""Serve the real app on a free local port, for the integration and browser tests."""
import socket
import threading
import time

import uvicorn

from app.main import app


def start():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True).start()
    while not server.started:
        time.sleep(0.01)
    return server, f"http://127.0.0.1:{sock.getsockname()[1]}"
