from pathlib import Path

from fastapi.testclient import TestClient

from app import create_app
from src.assist import LlmParts
from src.explain import NoExplainer
from src.router import NoRouter


def test_health_reports_local_mode_without_ollama_or_ports(tmp_path: Path) -> None:
    app = create_app(tmp_path / "t.db", LlmParts(NoExplainer(), NoRouter()))

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"mode": "local", "ollama": False, "explain": False, "ports": []}
