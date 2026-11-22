"""Malformed or out-of-range input never reaches a 500: huge ids, booleans, broken multipart."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src import service
from src.models import Sweep
from tests.test_api import UPLOAD, add_antenna, measure

HANGUL = re.compile("[가-힣]")
HUGE = 2**70
CSV = b"Frequency_Hz,S11_dB\n400e6,-1\n410e6,-20\n420e6,-1\n"


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "t.db"


@pytest.fixture
def client(db: Path) -> TestClient:
    return TestClient(create_app(db), raise_server_exceptions=False)


def korean_error(response: Any, status: int) -> bool:
    return response.status_code == status and bool(HANGUL.search(response.json()["detail"]))


@pytest.mark.parametrize("value", [HUGE, -HUGE, 2**63])
def test_ids_sqlite_cannot_hold_are_404(client: TestClient, value: int) -> None:
    body = {"antenna_id": value, "source": "synthetic", "sample": "good", "cal_mode": "vna"}
    form = {"antenna_id": str(value), "cal_mode": "vna"}
    files = {"file": ("s.csv", CSV, "text/csv")}

    assert korean_error(client.get(f"/api/measurements/{value}"), 404)
    assert korean_error(client.post("/api/measurements", json=body), 404)
    assert korean_error(client.post("/api/measurements/upload", files=files, data=form), 404)


def test_filter_by_an_id_sqlite_cannot_hold_is_empty(client: TestClient) -> None:
    response = client.get(f"/api/measurements?antenna_id={HUGE}")

    assert (response.status_code, response.json()) == (200, [])


def test_offset_sqlite_cannot_hold_is_422(client: TestClient) -> None:
    assert korean_error(client.get(f"/api/measurements?offset={HUGE}"), 422)


def test_largest_sqlite_offset_is_fine(client: TestClient) -> None:
    assert client.get(f"/api/measurements?offset={2**63 - 1}").json() == []


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/api/antennas", {"name": "a", "kind": "monopole", "target_mhz": True}),
        ("/api/measurements", {"antenna_id": True, "source": "synthetic", "sample": "good",
                               "cal_mode": "vna"}),
        ("/api/measurements", {"antenna_id": "1", "source": "synthetic", "sample": "good",
                               "cal_mode": "vna"}),
    ],
)  # fmt: skip
def test_booleans_and_strings_are_not_numbers(
    client: TestClient, path: str, body: dict[str, Any]
) -> None:
    add_antenna(client)

    assert korean_error(client.post(path, json=body), 422)
    assert client.get("/api/measurements").json() == []


def test_integer_target_is_still_a_number(client: TestClient) -> None:
    body = {"name": "a", "kind": "monopole", "target_mhz": 433}

    assert client.post("/api/antennas", json=body).json()["target_mhz"] == 433.0


@pytest.mark.parametrize(
    "headers",
    [{"content-type": "multipart/form-data"}, {"content-type": "multipart/form-data; boundary=x"}],
)
def test_broken_multipart_is_a_korean_422(client: TestClient, headers: dict[str, str]) -> None:
    response = client.post("/api/measurements/upload", content=b"not multipart", headers=headers)

    assert korean_error(response, 422)


def test_unknown_route_is_still_404(client: TestClient) -> None:
    assert client.get("/api/nope").status_code == 404


@dataclass
class OddSource:
    source: str = "radio"

    def read(self) -> Sweep:
        return Sweep(f_mhz=(420.0, 430.0, 440.0), s11_db=(-1.0, -20.0, -1.0))


def test_service_rejects_a_source_value_outside_the_list(client: TestClient, db: Path) -> None:
    antenna_id = add_antenna(client, target=430.0)
    request = service.MeasureInput(antenna_id=antenna_id, cal_mode="vna", change_note="")

    with pytest.raises(service.InputError, match="source"):
        service.measure(db, OddSource(), request)

    assert client.get("/api/measurements").json() == []


def test_unknown_ids_are_404(client: TestClient) -> None:
    assert measure(client, 999, "good").status_code == 404
    assert client.get("/api/measurements/999").status_code == 404
    form = {"antenna_id": "999", "cal_mode": "vna", "change_note": ""}
    files = {"file": ("s.csv", b"Frequency_Hz,S11_dB\n1,1\n2,2\n3,3\n", "text/csv")}
    response = client.post(UPLOAD, files=files, data=form)
    assert response.status_code == 404
    assert any("가" <= ch <= "힣" for ch in response.json()["detail"])


@pytest.mark.parametrize("target", [5.0, 1500.0])
def test_target_outside_the_sweep_is_422(client: TestClient, target: float) -> None:
    response = measure(client, add_antenna(client, target=target), "good")

    assert response.status_code == 422
    assert "목표" in response.json()["detail"]
    assert client.get("/api/measurements").json() == []


@pytest.mark.parametrize("query", ["stage=bad", "limit=0", "limit=201", "offset=-1", "limit=x"])
def test_bad_list_query_is_422(client: TestClient, query: str) -> None:
    assert client.get(f"/api/measurements?{query}").status_code == 422


def test_list_limit_defaults_to_50_and_allows_200(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    for _ in range(51):
        measure(client, antenna_id, "open")

    assert len(client.get("/api/measurements").json()) == 50
    assert len(client.get("/api/measurements?limit=200").json()) == 51
