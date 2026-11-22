"""A fake Ollama HTTP server on 127.0.0.1 for tests, and a port where nothing listens."""

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from src import ollama


@dataclass
class FakeOllama:
    """What the server answers, and the request bodies it received."""

    answer: str = ""
    answers: list[str] = field(default_factory=list)  # one per request, the last one repeats
    status: int = 200
    delay_s: float = 0.0
    raw_body: bytes | None = None
    extra_length: int = 0  # announce more bytes than are sent, so the body arrives cut short
    requests: list[dict[str, Any]] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)
    base_url: str = ""


def _answer(fake: FakeOllama) -> str:
    """`answers` in order when given (the request is already recorded), else `answer`."""
    if not fake.answers:
        return fake.answer
    return fake.answers[min(len(fake.requests), len(fake.answers)) - 1]


def _handler(fake: FakeOllama) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            fake.paths.append(self.path)
            fake.requests.append(json.loads(self.rfile.read(length)))
            time.sleep(fake.delay_s)
            body = fake.raw_body
            if body is None:
                body = json.dumps({"response": _answer(fake), "done": True}).encode()
            self.send_response(fake.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body) + fake.extra_length))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    return Handler


@contextmanager
def fake_ollama(answer: str = "", **settings: Any) -> Iterator[FakeOllama]:
    fake = FakeOllama(answer=answer, **settings)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(fake))
    server.daemon_threads = True
    fake.base_url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield fake
    finally:
        server.shutdown()
        server.server_close()


def record_timeouts(monkeypatch: Any) -> list[float]:
    """Replace the opener with one that records its timeout and refuses, so no request is sent."""
    timeouts: list[float] = []

    def refuse(request: Any, timeout: float) -> Any:
        timeouts.append(timeout)
        raise urllib.error.URLError("refused in test")

    monkeypatch.setattr(ollama, "open_direct", refuse)
    return timeouts


def closed_port_url() -> str:
    """A base URL whose port refuses connections."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}"
