"""Tests for the visual companion server and state broadcaster."""

from __future__ import annotations

import json
import urllib.request
from typing import Iterator

import pytest

from jarvis.visual import VisualBroadcaster, VisualServer, find_free_port


def test_broadcaster_initial_state() -> None:
    broadcaster = VisualBroadcaster()
    state = broadcaster.current_state
    assert state["status"] == "idle"
    assert state["text"] == ""
    assert isinstance(state["timestamp"], float)


def test_broadcaster_set_state_and_delivery() -> None:
    broadcaster = VisualBroadcaster()
    q = broadcaster.subscribe()

    # Initial state received immediately
    first = q.get_nowait()
    assert first.startswith("data: ")
    initial_data = json.loads(first.removeprefix("data: ").strip())
    assert initial_data["status"] == "idle"

    # Broadcast new state
    broadcaster.set_state("speaking", "Systems operational.")
    second = q.get_nowait()
    assert second.startswith("data: ")
    update_data = json.loads(second.removeprefix("data: ").strip())
    assert update_data["status"] == "speaking"
    assert update_data["text"] == "Systems operational."

    broadcaster.unsubscribe(q)


def test_broadcaster_drops_dead_subscribers() -> None:
    broadcaster = VisualBroadcaster()
    q = broadcaster.subscribe()

    # Fill the queue to capacity
    while not q.full():
        q.put_nowait("dummy")

    # Broadcasting to full queue should remove it safely without exception
    broadcaster.set_state("thinking", "testing drop")
    assert q not in broadcaster._subscribers


def test_find_free_port() -> None:
    port = find_free_port(5100, max_attempts=5)
    assert 5100 <= port < 5105


def test_visual_server_http_and_api() -> None:
    server = VisualServer(port=find_free_port(5200), auto_open=False)
    url = server.start()
    try:
        # Check /
        with urllib.request.urlopen(f"{url}/") as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            content = resp.read().decode("utf-8")
            assert "J.A.R.V.I.S. Aperture" in content

        # Check /visualizer.css
        with urllib.request.urlopen(f"{url}/visualizer.css") as resp:
            assert resp.status == 200
            assert "text/css" in resp.headers.get("Content-Type", "")
            css = resp.read().decode("utf-8")
            assert "--accent-glow" in css

        # Check /visualizer.js
        with urllib.request.urlopen(f"{url}/visualizer.js") as resp:
            assert resp.status == 200
            assert "javascript" in resp.headers.get("Content-Type", "")

        # Check /api/state
        server.set_state("listening", "Listening for wake word")
        with urllib.request.urlopen(f"{url}/api/state") as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "listening"
            assert data["text"] == "Listening for wake word"

        # Check 404
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{url}/not-exists.html")
        assert exc_info.value.code == 404
    finally:
        server.stop()


def test_visual_server_sse_stream() -> None:
    server = VisualServer(port=find_free_port(5250), auto_open=False)
    url = server.start()
    try:
        req = urllib.request.Request(f"{url}/events")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            assert "text/event-stream" in resp.headers.get("Content-Type", "")

            # Read initial line
            line1 = resp.readline().decode("utf-8")
            assert line1.startswith("data: ")
            _ = resp.readline()  # empty separator line

            # Trigger update
            server.set_state("thinking", "Testing SSE stream")
            line2 = resp.readline().decode("utf-8")
            assert line2.startswith("data: ")
            payload = json.loads(line2.removeprefix("data: ").strip())
            assert payload["status"] == "thinking"
            assert payload["text"] == "Testing SSE stream"
    finally:
        server.stop()


class DummyMouth:
    def __init__(self) -> None:
        self.said: list[str] = []
        self.error = None

    def say(self, text: str) -> None:
        self.said.append(text)

    def wait(self) -> None:
        pass


class DummyProvider:
    name = "dummy"
    model = "test-model"


class DummyBrain:
    def __init__(self, reply_pieces: list[str]) -> None:
        self.pieces = reply_pieces
        self.last_provider = DummyProvider()

    def ask(self, text: str) -> Iterator[str]:
        yield from self.pieces


class MockVisual:
    def __init__(self) -> None:
        self.history: list[tuple[str, str]] = []

    def set_state(self, status: str, text: str = "") -> None:
        self.history.append((status, text))


def test_greet_with_visual() -> None:
    from rich.console import Console
    from jarvis.voice import greet

    mouth = DummyMouth()
    visual = MockVisual()
    console = Console(quiet=True)

    greet(mouth, console, visual=visual)
    assert len(mouth.said) == 1
    assert ("speaking", mouth.said[0]) in visual.history
    assert visual.history[-1] == ("idle", "")


def test_respond_with_visual() -> None:
    from rich.console import Console
    from jarvis.voice import respond

    mouth = DummyMouth()
    visual = MockVisual()
    console = Console(quiet=True)
    brain = DummyBrain(["Good day. ", "How may I assist?"])

    respond(brain, mouth, console, "hello", visual=visual)
    statuses = [s for s, _ in visual.history]
    assert "speaking" in statuses
    assert visual.history[-1] == ("idle", "")


def test_abrupt_client_disconnect() -> None:
    """Verify that when a client abruptly closes an SSE socket, the server survives cleanly."""
    import socket
    import struct
    import time

    server = VisualServer(port=find_free_port(5300), auto_open=False)
    url = server.start()
    try:
        # Open raw socket and send GET /events
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", server.port))
        s.sendall(b"GET /events HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
        # Read the initial response
        data = s.recv(256)
        assert b"text/event-stream" in data

        # Force abrupt close on client side (RST/Abort)
        if hasattr(socket, "SO_LINGER"):
            s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
        s.close()

        # Trigger broadcasts to dead connection
        server.set_state("speaking", "Test speaking after client disconnected")
        server.set_state("idle")
        time.sleep(0.1)

        # Server should still be healthy and serve requests
        with urllib.request.urlopen(f"{url}/api/state") as resp:
            assert resp.status == 200
    finally:
        server.stop()



def test_broadcaster_close() -> None:
    b = VisualBroadcaster()
    q = b.subscribe()
    assert b._active is True
    b.close()
    assert b._active is False
    assert len(b._subscribers) == 0


def test_find_free_port_skips_occupied_port() -> None:
    import socket
    s = socket.socket()
    s.bind(('127.0.0.1', 5400))
    s.listen(1)
    try:
        next_port = find_free_port(5400, max_attempts=5)
        assert next_port == 5401
    finally:
        s.close()


def test_visual_server_auto_open(monkeypatch: pytest.MonkeyPatch) -> None:
    import time
    from jarvis import visual
    opened = []
    monkeypatch.setattr(visual, 'launch_app_window', lambda u: opened.append(u) or True)
    server = VisualServer(port=find_free_port(5450), auto_open=True)
    url = server.start()
    try:
        time.sleep(0.1)
        assert len(opened) == 1
        assert opened[0] == url
    finally:
        server.stop()


def test_launch_app_window_calls_popen_and_returns_true(monkeypatch: pytest.MonkeyPatch) -> None:
    import os
    import subprocess
    from jarvis.visual import launch_app_window

    calls = []

    class FakePopen:
        def __init__(self, cmd: list[str]) -> None:
            calls.append(cmd)

    monkeypatch.setattr(os.path, 'exists', lambda p: True)
    monkeypatch.setattr(subprocess, 'Popen', FakePopen)

    ok = launch_app_window('http://127.0.0.1:5050', width=400, height=600)
    assert ok is True
    assert len(calls) == 1
    assert '--app=http://127.0.0.1:5050' in calls[0]
    assert '--window-size=400,600' in calls[0]

    # When no candidate browser exists
    monkeypatch.setattr(os.path, 'exists', lambda p: False)
    assert launch_app_window('http://127.0.0.1:5050') is False


def test_visual_server_default_arguments() -> None:
    s = VisualServer()
    assert s.auto_open is True
    assert s.port >= 5050
