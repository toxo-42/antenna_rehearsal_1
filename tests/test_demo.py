"""APP_MODE=demo: stored measurements only, no writes, no USB, no local model."""

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app as app_module
from app import create_app
from src import store
from src.assist import LlmParts
from src.synthetic import SAMPLE_NAMES

DATA = Path(__file__).resolve().parent / "data"
DEMO_TEXT = "시연 모드"


@pytest.fixture
def db(tmp_path: Path) -> Path:
    """One antenna with one synthetic measurement, saved in local mode."""
    path = tmp_path / "demo.db"
    local = TestClient(create_app(path))
    body = {"name": "a", "kind": "monopole", "target_mhz": 433.0}
    antenna_id = local.post("/api/antennas", json=body).json()["id"]
    sample = {"antenna_id": antenna_id, "source": "synthetic", "sample": SAMPLE_NAMES[0],
              "cal_mode": "vna", "change_note": ""}  # fmt: skip
    assert local.post("/api/measurements", json=sample).status_code == 200
    return path


@pytest.fixture
def opened() -> list[str]:
    return []


@pytest.fixture
def demo(db: Path, opened: list[str]) -> TestClient:
    client = TestClient(create_app(db, mode="demo"))

    def opener(name: str) -> Any:
        opened.append(name)
        raise AssertionError("demo mode opened a serial port")

    client.app.state.serial_opener = opener  # type: ignore[attr-defined]
    return client


def counts(db: Path) -> tuple[int, int]:
    with sqlite3.connect(db) as conn:
        antennas = conn.execute("SELECT COUNT(*) FROM antennas").fetchone()[0]
        measurements = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    return antennas, measurements


def measurement_body(source: str) -> dict[str, Any]:
    body: dict[str, Any] = {"antenna_id": 1, "source": source, "cal_mode": "vna"}
    if source == "synthetic":
        return body | {"sample": SAMPLE_NAMES[0]}
    return body | {"port": "/dev/fake", "start_mhz": 400.0, "stop_mhz": 470.0, "points": 101}


WRITES = {
    "antenna": lambda c: c.post(
        "/api/antennas", json={"name": "b", "kind": "patch", "target_mhz": 2450.0}
    ),
    "synthetic measurement": lambda c: c.post(
        "/api/measurements", json=measurement_body("synthetic")
    ),
    "usb measurement": lambda c: c.post("/api/measurements", json=measurement_body("usb")),
    "upload": lambda c: c.post(
        "/api/measurements/upload",
        files={"file": ("s.csv", (DATA / "monopole_12cm.csv").read_bytes(), "text/csv")},
        data={"antenna_id": "1", "cal_mode": "vna", "change_note": ""},
    ),
    "device screen": lambda c: c.get("/api/device/screen", params={"port": "/dev/fake"}),
    "ports": lambda c: c.get("/api/ports"),
}


@pytest.mark.parametrize("name", WRITES)
def test_demo_refuses_writes_and_usb_with_403(
    name: str, demo: TestClient, db: Path, opened: list[str]
) -> None:
    before = counts(db)

    response = WRITES[name](demo)

    assert response.status_code == 403, response.text[:200]
    assert DEMO_TEXT in response.json()["detail"]
    assert counts(db) == before
    assert opened == []


@pytest.mark.parametrize("name", ["antenna", "synthetic measurement", "upload"])
def test_local_mode_still_allows_the_same_writes(name: str, db: Path) -> None:
    response = WRITES[name](TestClient(create_app(db)))

    assert response.status_code == 200, response.text


@pytest.mark.parametrize(
    "path",
    ["/api/antennas", "/api/samples", "/api/measurements", "/api/measurements/1",
     "/api/measurements/1/guides", "/api/compare?before=1&after=1"],
)  # fmt: skip
def test_demo_still_reads_stored_measurements(path: str, demo: TestClient) -> None:
    response = demo.get(path)

    assert response.status_code == 200, response.text


class RecordingModel:
    """Stands in for both local-model parts and records every call it gets."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def explain(self, card: Any, antenna: Any) -> Any:
        self.calls.append("explain")
        raise AssertionError("demo mode called the explainer")

    def choose(self, question: str, kind: Any) -> int | None:
        self.calls.append("choose")
        return 1


def test_demo_health_turns_the_local_model_off_even_when_given(db: Path) -> None:
    model = RecordingModel()
    client = TestClient(create_app(db, LlmParts(model, model), mode="demo"))  # type: ignore[arg-type]

    health = client.get("/api/health").json()
    explained = client.post("/api/measurements/1/explain").json()
    asked = client.post("/api/measurements/1/ask", json={"question": "왜 이렇게 나와요?"}).json()

    assert health == {"mode": "demo", "ollama": False, "explain": False, "ports": []}
    assert explained["status"] == "off"
    assert asked["status"] == "failed"
    assert model.calls == []


def test_the_same_model_parts_are_used_in_local_mode(db: Path) -> None:
    model = RecordingModel()
    client = TestClient(create_app(db, LlmParts(model, model)))  # type: ignore[arg-type]

    asked = client.post("/api/measurements/1/ask", json={"question": "왜 이렇게 나와요?"}).json()

    assert asked["status"] == "matched"
    assert model.calls == ["choose"]


def test_demo_without_its_database_refuses_to_start(tmp_path: Path) -> None:
    missing = tmp_path / "demo.db"

    with pytest.raises(FileNotFoundError, match="export_demo.py"):
        create_app(missing, mode="demo")
    assert not missing.exists()


def test_demo_without_a_path_opens_demo_db_not_the_local_history(
    db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = tmp_path / "local.db"
    monkeypatch.setattr(app_module, "DEMO_DB", db)
    monkeypatch.setattr(app_module, "DEFAULT_DB", local)

    client = TestClient(create_app(mode="demo"))

    assert len(client.get("/api/measurements").json()) == 1
    assert not local.exists()


@pytest.mark.parametrize("content", ["empty file", "tables without measurements"])
def test_demo_db_without_measurements_refuses_to_start(content: str, tmp_path: Path) -> None:
    path = tmp_path / "demo.db"
    path.write_bytes(b"")
    if content == "tables without measurements":
        store.init_db(path)
    size = path.stat().st_size

    with pytest.raises(ValueError, match="export_demo.py"):
        create_app(path, mode="demo")
    assert path.stat().st_size == size  # nothing was created in it


def test_count_measurements(db: Path, tmp_path: Path) -> None:
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")

    assert store.count_measurements(db) == 1
    assert store.count_measurements(empty) == 0
    assert empty.stat().st_size == 0


def test_unknown_mode_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="APP_MODE"):
        create_app(tmp_path / "t.db", mode="dmo")


def test_env_demo_uses_demo_db_and_env_default_is_local(
    db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_module, "DEMO_DB", db)
    monkeypatch.setattr(app_module, "DEFAULT_DB", tmp_path / "local.db")

    from_env = app_module.create_app_from_env
    demo = TestClient(from_env({"APP_MODE": "demo", "OLLAMA_MODEL": "m"}))
    local = TestClient(from_env({"OLLAMA_MODEL": ""}))

    assert demo.get("/api/health").json()["mode"] == "demo"
    assert len(demo.get("/api/measurements").json()) == 1
    assert local.get("/api/health").json()["mode"] == "local"
    assert local.get("/api/measurements").json() == []


@pytest.mark.parametrize("value", ["demo", " Demo ", "DEMO"])
def test_env_mode_ignores_case_and_spaces(
    value: str, db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_module, "DEMO_DB", db)

    client = TestClient(app_module.create_app_from_env({"APP_MODE": value}))

    assert client.get("/api/health").json()["mode"] == "demo"


def test_env_demo_without_demo_db_refuses_to_start(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "demo.db"
    monkeypatch.setattr(app_module, "DEMO_DB", missing)

    with pytest.raises(FileNotFoundError, match="export_demo.py"):
        app_module.create_app_from_env({"APP_MODE": "demo"})
    assert not missing.exists()


def test_env_typo_in_mode_is_refused_instead_of_running_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(app_module, "DEFAULT_DB", tmp_path / "local.db")

    with pytest.raises(ValueError, match="APP_MODE"):
        app_module.create_app_from_env({"APP_MODE": "dmo"})


def test_demo_serves_the_built_screen_at_the_same_address(
    db: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<div id=root></div>", encoding="utf-8")
    monkeypatch.setattr(app_module, "WEB_DIST", dist)

    client = TestClient(create_app(db, mode="demo"))

    assert client.get("/").text == "<div id=root></div>"
    assert client.get("/api/health").json()["mode"] == "demo"
