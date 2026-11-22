"""One call to a local Ollama `/api/generate` with the standard library. Nothing leaves 127.0.0.1."""

import http.client
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3.5:4b"
KEEP_ALIVE = "10m"
# No proxy, whatever HTTP_PROXY or the system says: the request must stay on this PC.
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class OllamaError(RuntimeError):
    """Ollama could not be reached, timed out, or answered something unusable."""


@dataclass(frozen=True)
class GenerateRequest:
    model: str
    prompt: str
    options: dict[str, Any]
    timeout_s: float


def generate(base_url: str, request: GenerateRequest) -> str:
    """The `response` text of one non-streaming generation. `format` is never sent:
    the Homebrew build 0.40.16 answers it with HTTP 501."""
    body = {
        "model": request.model,
        "prompt": request.prompt,
        "stream": False,
        "think": False,
        "keep_alive": KEEP_ALIVE,
        "options": request.options,
    }
    http_request = urllib.request.Request(
        f"{base_url}/api/generate",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with open_direct(http_request, request.timeout_s) as response:
            raw = response.read()
    except (urllib.error.URLError, http.client.HTTPException, OSError) as error:
        # HTTPException covers a body cut short (IncompleteRead); OSError covers timeouts.
        raise OllamaError(str(error)) from error
    return _response_text(raw)


def open_direct(http_request: urllib.request.Request, timeout_s: float) -> Any:
    """Send `http_request` without any proxy."""
    return _DIRECT.open(http_request, timeout=timeout_s)


def _response_text(raw: bytes) -> str:
    try:
        answer = json.loads(raw)
    except ValueError as error:
        raise OllamaError("Ollama response is not JSON") from error
    text = answer.get("response") if isinstance(answer, dict) else None
    if not isinstance(text, str):
        raise OllamaError("Ollama response has no text")
    return text
