import pytest

from src.ollama import GenerateRequest, generate
from tests.fake_ollama import fake_ollama

REQUEST = GenerateRequest(model="m", prompt="p", options={}, timeout_s=5.0)
PROXY_VARIABLES = ("HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy")
BYPASS_VARIABLES = ("NO_PROXY", "no_proxy")


@pytest.mark.parametrize("variable", PROXY_VARIABLES)
def test_proxy_settings_never_reroute_the_local_model_request(
    variable: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Measurement values stay on this PC even where a proxy is set (e.g. a school PC)."""
    for name in PROXY_VARIABLES + BYPASS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    with fake_ollama("direct") as ollama, fake_ollama("via proxy") as proxy:
        monkeypatch.setenv(variable, proxy.base_url)
        text = generate(ollama.base_url, REQUEST)
    assert proxy.requests == []
    assert len(ollama.requests) == 1
    assert text == "direct"
