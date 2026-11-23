"""Manage page: antenna overview, rename, and deleting measurements and antennas."""

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src.synthetic import SAMPLE_NAMES


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "t.db"


@pytest.fixture
def client(db: Path) -> TestClient:
    return TestClient(create_app(db))


def add_antenna(client: TestClient, name: str = "a") -> int:
    body = {"name": name, "kind": "monopole", "target_mhz": 433.0}
    return client.post("/api/antennas", json=body).json()["id"]


def measure(client: TestClient, antenna_id: int, sample: str = "good") -> int:
    body = {"antenna_id": antenna_id, "source": "synthetic", "sample": sample, "cal_mode": "vna"}
    response = client.post("/api/measurements", json=body)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def counts(db: Path) -> tuple[int, int]:
    with sqlite3.connect(db) as conn:
        antennas = conn.execute("SELECT COUNT(*) FROM antennas").fetchone()[0]
        measurements = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    return antennas, measurements


def overview(client: TestClient) -> dict[int, dict[str, Any]]:
    response = client.get("/api/antennas/overview")
    assert response.status_code == 200, response.text
    return {row["id"]: row for row in response.json()}


def test_overview_counts_measurements_and_shows_the_newest(client: TestClient) -> None:
    empty, used = add_antenna(client, "empty"), add_antenna(client, "used")
    measure(client, used, "good")
    newest = client.get(f"/api/measurements/{measure(client, used, 'offtarget_low')}").json()
    rows = overview(client)
    assert list(rows) == [empty, used]
    assert rows[empty] | {"id": 0} == {
        "id": 0, "name": "empty", "kind": "monopole", "target_mhz": 433.0,
        "measurement_count": 0, "last_measured_at": None, "last_stage": None,
        "last_resonance_mhz": None,
    }  # fmt: skip
    assert rows[used]["measurement_count"] == 2
    assert rows[used]["last_stage"] == newest["card"]["stage"] == "offtarget"
    assert rows[used]["last_resonance_mhz"] == newest["resonance_mhz"]
    assert rows[used]["last_measured_at"] == newest["measured_at"]


def test_rename_changes_only_the_name(client: TestClient) -> None:
    antenna_id = add_antenna(client, "old")
    measurement_id = measure(client, antenna_id)
    response = client.patch(f"/api/antennas/{antenna_id}", json={"name": "새 이름"})
    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": antenna_id,
        "name": "새 이름",
        "kind": "monopole",
        "target_mhz": 433.0,
    }
    assert client.get("/api/antennas").json() == [response.json()]
    assert client.get(f"/api/measurements/{measurement_id}").json()["antenna"]["name"] == "새 이름"


@pytest.mark.parametrize("name", ["", "   "])
def test_rename_refuses_an_empty_name(client: TestClient, name: str) -> None:
    antenna_id = add_antenna(client, "old")
    response = client.patch(f"/api/antennas/{antenna_id}", json={"name": name})
    assert response.status_code == 422
    assert "이름" in response.json()["detail"]
    assert client.get("/api/antennas").json()[0]["name"] == "old"


def test_rename_cannot_change_kind_or_target(client: TestClient) -> None:
    antenna_id = add_antenna(client, "old")
    body = {"name": "n", "kind": "patch", "target_mhz": 2450.0}
    assert client.patch(f"/api/antennas/{antenna_id}", json=body).status_code == 422
    assert client.get("/api/antennas").json()[0] == {
        "id": antenna_id, "name": "old", "kind": "monopole", "target_mhz": 433.0,
    }  # fmt: skip


def test_delete_measurement_removes_that_one_only(client: TestClient, db: Path) -> None:
    antenna_id = add_antenna(client)
    first, second = measure(client, antenna_id), measure(client, antenna_id)
    response = client.delete(f"/api/measurements/{first}")
    assert response.status_code == 200, response.text
    assert counts(db) == (1, 1)
    assert client.get(f"/api/measurements/{first}").status_code == 404
    assert client.get(f"/api/measurements/{second}").status_code == 200


def test_delete_antenna_removes_its_measurements_and_nothing_else(
    client: TestClient, db: Path
) -> None:
    gone, kept = add_antenna(client, "gone"), add_antenna(client, "kept")
    measure(client, gone), measure(client, gone)
    kept_measurement = measure(client, kept)
    response = client.delete(f"/api/antennas/{gone}")
    assert response.status_code == 200, response.text
    assert response.json() == {"deleted_measurements": 2}
    assert counts(db) == (1, 1)
    assert [row["id"] for row in client.get("/api/antennas").json()] == [kept]
    assert client.get(f"/api/measurements/{kept_measurement}").status_code == 200


@pytest.mark.parametrize("missing", [999, 2**63, -1])
def test_what_does_not_exist_is_a_404_and_changes_nothing(
    client: TestClient, db: Path, missing: int
) -> None:
    measure(client, add_antenna(client))
    for response in (
        client.delete(f"/api/measurements/{missing}"),
        client.delete(f"/api/antennas/{missing}"),
        client.patch(f"/api/antennas/{missing}", json={"name": "n"}),
    ):
        assert response.status_code == 404, response.text
        assert "없습니다" in response.json()["detail"]
    assert counts(db) == (1, 1)


def test_demo_mode_refuses_rename_and_deletes_but_shows_the_overview(db: Path) -> None:
    local = TestClient(create_app(db))
    antenna_id = add_antenna(local)
    measurement_id = measure(local, antenna_id, SAMPLE_NAMES[0])
    demo = TestClient(create_app(db, mode="demo"))
    for response in (
        demo.patch(f"/api/antennas/{antenna_id}", json={"name": "n"}),
        demo.delete(f"/api/antennas/{antenna_id}"),
        demo.delete(f"/api/measurements/{measurement_id}"),
    ):
        assert response.status_code == 403, response.text
    assert counts(db) == (1, 1)
    assert demo.get("/api/antennas").json()[0]["name"] == "a"
    assert overview(demo)[antenna_id]["measurement_count"] == 1
