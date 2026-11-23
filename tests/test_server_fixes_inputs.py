"""Input edges: conductor length range and form text, text that is not UTF-8, ids never reused,
and the source of the newest measurement in the overview."""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src.length import check_length, parse_length
from tests.test_api import add_antenna

DATA = Path(__file__).resolve().parent / "data"
JSON = {"content-type": "application/json"}
LONE = "\ud800"  # a lone surrogate: a JSON body may carry it, UTF-8 cannot


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "t.db"


@pytest.fixture
def client(db: Path) -> TestClient:
    return TestClient(create_app(db), raise_server_exceptions=False)


def counts(db: Path) -> tuple[int, int]:
    with sqlite3.connect(db) as conn:
        antennas = conn.execute("SELECT COUNT(*) FROM antennas").fetchone()[0]
        measurements = conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    return antennas, measurements


def korean_422(response: Any) -> bool:
    return response.status_code == 422 and any("가" <= c <= "힣" for c in response.json()["detail"])


def sample(client: TestClient, antenna_id: int, **extra: Any) -> Any:
    body = {"antenna_id": antenna_id, "source": "synthetic", "sample": "good", "cal_mode": "vna"}
    return client.post("/api/measurements", content=_json({**body, **extra}), headers=JSON)


def _json(body: dict[str, Any]) -> bytes:
    return json.dumps(body).encode("ascii")  # keeps \ud800 as an escape


def upload(client: TestClient, **form: str) -> Any:
    data = (DATA / "monopole_12cm.csv").read_bytes()
    fields = {"cal_mode": "vna", **form}
    return client.post("/api/measurements/upload", data=fields, files={"file": ("s.csv", data)})


@pytest.mark.parametrize("value", [1e-308, 0.0999, 0.0, -1.0, 1000.01, float("inf")])
def test_a_length_outside_the_range_is_refused(value: float) -> None:
    with pytest.raises(ValueError, match="0.1 cm 이상 1000 cm 이하"):
        check_length(value)


@pytest.mark.parametrize("value", [0.1, 12.0, 1000.0])
def test_a_length_inside_the_range_is_kept(value: float) -> None:
    assert check_length(value) == value
    assert parse_length(f" {value} ") == value


@pytest.mark.parametrize("written", ["1e3", "1_0", "１２", "+12", "12.", ".5", "1e-308", "nan"])
def test_form_text_must_be_a_plain_decimal(written: str) -> None:
    with pytest.raises(ValueError, match="길이"):
        parse_length(written)


def test_a_tiny_length_is_a_422_on_both_paths(client: TestClient, db: Path) -> None:
    antenna_id = add_antenna(client)

    assert korean_422(sample(client, antenna_id, length_cm=1e-308))
    assert korean_422(upload(client, antenna_id=str(antenna_id), length_cm="1e-308"))
    assert korean_422(upload(client, antenna_id=str(antenna_id), length_cm="1e3"))
    assert counts(db) == (1, 0)


@pytest.mark.parametrize("written", ["1.0", "１", "+1", "1_0", " 1", ""])
def test_the_upload_antenna_id_must_be_ascii_digits(
    written: str, client: TestClient, db: Path
) -> None:
    add_antenna(client)

    assert korean_422(upload(client, antenna_id=written))
    assert counts(db) == (1, 0)


def test_the_upload_still_takes_a_plain_id(client: TestClient) -> None:
    antenna_id = add_antenna(client)

    assert upload(client, antenna_id=str(antenna_id), length_cm="12").status_code == 200
    assert upload(client, antenna_id="-1").status_code == 404
    assert upload(client, antenna_id="9" * 30).status_code == 404
    assert korean_422(upload(client, antenna_id="9" * 5000))  # more digits than int() reads


@pytest.mark.parametrize("field", ["name", "kind"])
def test_an_antenna_field_that_is_not_utf8_is_a_422(
    field: str, client: TestClient, db: Path
) -> None:
    body = {"name": "a", "kind": "monopole", "target_mhz": 433.0} | {field: f"x{LONE}"}

    assert korean_422(client.post("/api/antennas", content=_json(body), headers=JSON))
    assert counts(db) == (0, 0)


@pytest.mark.parametrize("field", ["change_note", "sample", "source", "cal_mode", "port"])
def test_a_measurement_field_that_is_not_utf8_is_a_422(
    field: str, client: TestClient, db: Path
) -> None:
    antenna_id = add_antenna(client)

    assert korean_422(sample(client, antenna_id, **{field: f"x{LONE}"}))
    assert counts(db) == (1, 0)


def test_a_rename_or_a_question_that_is_not_utf8_is_a_422(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    measurement_id = sample(client, antenna_id).json()["id"]

    renamed = client.patch(
        f"/api/antennas/{antenna_id}", content=_json({"name": LONE}), headers=JSON
    )
    asked = client.post(
        f"/api/measurements/{measurement_id}/ask",
        content=_json({"question": f"왜{LONE}"}),
        headers=JSON,
    )

    assert korean_422(renamed)
    assert korean_422(asked)
    assert client.get("/api/antennas").json()[0]["name"] == "a"


def test_a_deleted_antenna_id_is_not_given_again(client: TestClient) -> None:
    first, newest = add_antenna(client), add_antenna(client)

    assert client.delete(f"/api/antennas/{newest}").status_code == 200

    assert add_antenna(client) > newest > first


def test_a_deleted_measurement_id_is_not_given_again(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    sample(client, antenna_id)
    newest = sample(client, antenna_id).json()["id"]

    assert client.delete(f"/api/measurements/{newest}").status_code == 200

    assert sample(client, antenna_id).json()["id"] > newest


def test_the_overview_carries_the_source_of_the_newest_measurement(client: TestClient) -> None:
    empty, used = add_antenna(client), add_antenna(client)
    sample(client, used)
    assert upload(client, antenna_id=str(used)).status_code == 200

    rows = {row["id"]: row for row in client.get("/api/antennas/overview").json()}

    assert rows[empty]["last_source"] is None
    assert rows[used]["last_source"] == "csv"
