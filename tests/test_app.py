import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app as app_module
from app import ROOT, create_app
from src.assist import LlmParts
from src.explain import NoExplainer
from src.router import NoRouter


def test_health_reports_local_mode_without_ollama_or_ports(tmp_path: Path) -> None:
    app = create_app(tmp_path / "t.db", LlmParts(NoExplainer(), NoRouter()))

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"mode": "local", "ollama": False, "explain": False, "ports": []}


def test_importing_the_module_builds_no_app_and_opens_no_database() -> None:
    """`from app import create_app` (every test does it) must not touch the real antenna.db.
    A mode that cannot start shows it: building the app at import time would raise here."""
    env = {**os.environ, "APP_MODE": "no-such-mode"}

    command = [sys.executable, "-c", "import app"]
    done = subprocess.run(command, check=False, cwd=ROOT, env=env, capture_output=True, text=True)

    assert done.returncode == 0, done.stderr


def test_the_server_entry_point_builds_the_app_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    built = FastAPI()
    monkeypatch.setattr(app_module, "create_app_from_env", lambda env: built)

    assert app_module.app is built  # what `uvicorn app:app` loads
    with pytest.raises(AttributeError):
        _ = app_module.no_such_name


@pytest.mark.parametrize("path", ["/docs", "/redoc"])
def test_pages_that_load_scripts_from_the_internet_are_off(path: str, tmp_path: Path) -> None:
    app = create_app(tmp_path / "t.db", LlmParts(NoExplainer(), NoRouter()))

    assert TestClient(app).get(path).status_code == 404
