"""Lightweight, zero-dependency visual companion server for Jarvis.

Uses Python standard library (http.server + Server-Sent Events) to stream
state transitions (idle, listening, thinking, speaking) and live speech subtitles
to a browser-based animated HUD aperture.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import socket
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

STATIC_DIR = Path(__file__).resolve().parent / "static"
logger = logging.getLogger("jarvis.visual")


class VisualBroadcaster:
    """Thread-safe event bus that broadcasts state events to connected SSE clients."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue[str | None]] = []
        self._active = True
        self._current_state: dict[str, Any] = {
            "status": "idle",
            "text": "",
            "timestamp": time.time(),
        }

    @property
    def current_state(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._current_state)

    def set_state(self, status: str, text: str = "") -> None:
        """Update current state and notify all connected clients."""
        with self._lock:
            if not self._active:
                return
            payload = {
                "status": status,
                "text": text,
                "timestamp": time.time(),
            }
            self._current_state = payload
            message = f"data: {json.dumps(payload)}\n\n"
            dead: list[queue.Queue[str | None]] = []
            for q in self._subscribers:
                try:
                    q.put_nowait(message)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._subscribers.remove(q)

    def subscribe(self) -> queue.Queue[str | None]:
        """Register a new SSE client queue, pre-populated with current state."""
        q: queue.Queue[str | None] = queue.Queue(maxsize=100)
        with self._lock:
            initial = f"data: {json.dumps(self._current_state)}\n\n"
            q.put_nowait(initial)
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[str | None]) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def close(self) -> None:
        with self._lock:
            self._active = False
            for q in self._subscribers:
                try:
                    q.put_nowait(None)
                except queue.Full:
                    pass
            self._subscribers.clear()


class VisualHandler(BaseHTTPRequestHandler):
    """Handles static asset serving and Server-Sent Events stream."""

    broadcaster: VisualBroadcaster = VisualBroadcaster()

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard HTTP access logs in console
        pass

    def handle_one_request(self) -> None:
        try:
            super().handle_one_request()
        except (ConnectionError, OSError):
            self.close_connection = True

    def do_GET(self) -> None:
        try:
            path = self.path.split("?")[0].rstrip("/")
            if path in {"", "/index.html"}:
                self._serve_file(STATIC_DIR / "visualizer.html", "text/html; charset=utf-8")
            elif path == "/visualizer.css":
                self._serve_file(STATIC_DIR / "visualizer.css", "text/css; charset=utf-8")
            elif path == "/visualizer.js":
                self._serve_file(STATIC_DIR / "visualizer.js", "application/javascript; charset=utf-8")
            elif path == "/api/state":
                body = json.dumps(self.broadcaster.current_state).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
                self.close_connection = True
            elif path == "/favicon.ico":
                self.send_response(HTTPStatus.NO_CONTENT)
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True
            elif path == "/events":
                self._handle_sse()
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "File not found")
        except (ConnectionError, OSError):
            self.close_connection = True

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        if not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Asset not found")
            return
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(data)
        self.close_connection = True

    def _handle_sse(self) -> None:
        try:
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        except (ConnectionError, OSError):
            return

        client_queue = self.broadcaster.subscribe()
        try:
            while True:
                try:
                    event = client_queue.get(timeout=1.0)
                    if event is None:
                        break
                    self.wfile.write(event.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive heartbeat
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (ConnectionError, OSError):
            pass
        finally:
            self.broadcaster.unsubscribe(client_queue)


def find_free_port(start_port: int = 5050, max_attempts: int = 20) -> int:
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start_port


class SilentThreadingHTTPServer(ThreadingHTTPServer):
    """Threading HTTPServer that suppresses noisy tracebacks when clients close browser tabs."""

    daemon_threads = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        import sys

        _, exc, _ = sys.exc_info()
        if isinstance(exc, (ConnectionError, OSError)):
            return
        super().handle_error(request, client_address)


def launch_app_window(url: str, width: int = 420, height: int = 580) -> bool:
    """Launch the HUD in a standalone, frameless desktop window using Edge or Chrome app mode."""
    candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for exe in candidates:
        if os.path.exists(exe):
            try:
                import subprocess

                subprocess.Popen([
                    exe,
                    f"--app={url}",
                    f"--window-size={width},{height}",
                ])
                return True
            except Exception:
                pass
    return False


class VisualServer:
    """Manages the background visual HTTP/SSE server."""

    def __init__(self, port: int = 5050, auto_open: bool = True) -> None:
        self.broadcaster = VisualBroadcaster()
        self.port = find_free_port(port)
        self.auto_open = auto_open
        self._server: SilentThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        handler_class = type(
            "BoundVisualHandler",
            (VisualHandler,),
            {"broadcaster": self.broadcaster},
        )
        self._server = SilentThreadingHTTPServer(("127.0.0.1", self.port), handler_class)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        url = f"http://127.0.0.1:{self.port}"
        if self.auto_open and os.environ.get("JARVIS_NO_BROWSER") != "1":
            def _open():
                if not launch_app_window(url):
                    webbrowser.open(url)

            threading.Thread(target=_open, daemon=True).start()
        return url

    def set_state(self, status: str, text: str = "") -> None:
        self.broadcaster.set_state(status, text=text)

    def stop(self) -> None:
        self.broadcaster.close()
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
