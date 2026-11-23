"""The conductor length entered with a measurement: stored with it, used for the verdict."""

import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src import store
from tests.test_api import add_antenna

DATA = Path(__file__).resolve().parent / "data"
OLD_SCHEMA = store.SCHEMA.replace(",\n    length_cm REAL", "")


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "t.db"


@pytest.fixture
def client(db: Path) -> TestClient:
    return TestClient(create_app(db), raise_server_exceptions=False)


def upload_12cm(client: TestClient, antenna_id: int, length: str | None = None) -> Any:
    form = {"antenna_id": str(antenna_id), "cal_mode": "vna"}
    if length is not None:
        form["length_cm"] = length
    data = (DATA / "monopole_12cm.csv").read_bytes()
    return client.post("/api/measurements/upload", data=form, files={"file": ("s.csv", data)})


def sample(client: TestClient, antenna_id: int, **extra: Any) -> Any:
    body = {"antenna_id": antenna_id, "source": "synthetic", "sample": "good", "cal_mode": "vna"}
    return client.post("/api/measurements", json={**body, **extra})


def test_without_a_length_nothing_changes(client: TestClient) -> None:
    antenna_id = add_antenna(client, "monopole", 433.0)

    got = upload_12cm(client, antenna_id).json()

    assert got["length_cm"] is None
    assert got["card"]["stage"] == "none"
    assert not any("예상" in line for line in got["card"]["status"])


def test_an_uploaded_length_is_stored_and_used(client: TestClient) -> None:
    antenna_id = add_antenna(client, "monopole", 433.0)

    created = upload_12cm(client, antenna_id, "12")

    assert created.status_code == 200, created.text
    got = client.get(f"/api/measurements/{created.json()['id']}").json()
    assert got == created.json()
    assert got["length_cm"] == 12.0
    assert got["resonance_mhz"] == pytest.approx(622.95)
    assert got["card"]["stage"] == "unmatched"
    assert "예상 공진 625.00 MHz (도체 길이 12 cm)" in got["card"]["status"]
    assert got["card"]["diagnoses"][0]["key"] == "too_short"
    row = client.get(f"/api/measurements?antenna_id={antenna_id}").json()[0]
    assert row["length_cm"] == 12.0


def test_a_json_measurement_takes_the_length_too(client: TestClient) -> None:
    antenna_id = add_antenna(client, "monopole", 433.0)

    assert sample(client, antenna_id, length_cm=17.3).json()["length_cm"] == 17.3
    assert sample(client, antenna_id, length_cm=17).json()["length_cm"] == 17.0
    assert sample(client, antenna_id, length_cm=None).json()["length_cm"] is None


@pytest.mark.parametrize("value", [0, -1, 1000.1, True, "12"])
def test_a_bad_json_length_is_422(client: TestClient, value: Any) -> None:
    antenna_id = add_antenna(client, "monopole", 433.0)

    response = sample(client, antenna_id, length_cm=value)

    assert response.status_code == 422, response.text
    assert client.get("/api/measurements").json() == []


@pytest.mark.parametrize("value", ["0", "-3", "nan", "inf", "abc", "1e9"])
def test_a_bad_uploaded_length_is_422(client: TestClient, value: str) -> None:
    antenna_id = add_antenna(client, "monopole", 433.0)

    response = upload_12cm(client, antenna_id, value)

    assert response.status_code == 422, response.text
    assert client.get("/api/measurements").json() == []


def test_a_bad_length_is_explained_in_korean(client: TestClient) -> None:
    antenna_id = add_antenna(client, "monopole", 433.0)

    detail = sample(client, antenna_id, length_cm=0).json()["detail"]

    assert "길이" in detail and "cm" in detail


def test_a_patch_measurement_does_not_keep_a_length(client: TestClient) -> None:
    antenna_id = add_antenna(client, "patch", 433.0)

    assert sample(client, antenna_id, length_cm=12.0).json()["length_cm"] is None


def test_an_empty_uploaded_length_means_not_entered(client: TestClient) -> None:
    antenna_id = add_antenna(client, "monopole", 433.0)

    assert upload_12cm(client, antenna_id, "").json()["length_cm"] is None


def test_a_database_from_before_the_column_keeps_working(db: Path) -> None:
    with sqlite3.connect(db) as conn:
        conn.executescript(OLD_SCHEMA)
        conn.execute("INSERT INTO antennas (name, kind, target_mhz) VALUES ('a', 'monopole', 433)")
        conn.execute(
            "INSERT INTO measurements (antenna_id, measured_at, source, cal_mode, stage, "
            "sweep_json, card_json, change_note) VALUES (1, 't', 'csv', 'vna', 'none', '[]', "
            '\'{"stage": "none", "headline": "", "status": [], "diagnoses": []}\', \'\')'
        )
    conn.close()
    assert "length_cm" not in OLD_SCHEMA

    client = TestClient(create_app(db))

    assert client.get("/api/measurements/1").json()["length_cm"] is None
    assert upload_12cm(client, 1, "12").json()["length_cm"] == 12.0
    TestClient(create_app(db))  # starting again does not add the column twice
