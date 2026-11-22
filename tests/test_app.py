from fastapi.testclient import TestClient

from app import app


def test_health_reports_local_mode_without_ollama_or_ports() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"mode": "local", "ollama": False, "ports": []}
