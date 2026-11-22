"""Boundaries and paths the main API tests leave open: order, ranges, size, time, null, errors."""

import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src import api, service, store
from src.models import Sweep
from src.sources import StoredSource
from src.synthetic import make_sample
from tests.test_api import add_antenna, csv_text, measure, upload

HANGUL = re.compile("[가-힣]")
MB2 = 2 * 1024 * 1024


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "t.db"


@pytest.fixture
def client(db: Path) -> TestClient:
    return TestClient(create_app(db))


def insert_row(db: Path, antenna_id: int, measured_at: str, **changes: Any) -> int:
    sweep = Sweep(f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, -20.0, -1.0))
    values: dict[str, Any] = {
        "antenna_id": antenna_id, "measured_at": measured_at, "source": "csv",
        "cal_mode": "vna", "stage": "good", "resonance_mhz": 410.0, "s11_db": -20.0,
        "bandwidth_pct": 1.0, "sweep_json": store.sweep_to_json(sweep), "card_json": "{}",
        "change_note": "",
    }  # fmt: skip
    with store.connect(db) as conn:
        return store.insert_measurement(conn, store.NewMeasurement(**(values | changes)))


def test_list_orders_by_time_before_id(client: TestClient, db: Path) -> None:
    antenna_id = add_antenna(client)
    later = insert_row(db, antenna_id, "2026-11-22T12:00:00")
    earlier = insert_row(db, antenna_id, "2026-11-22T09:00:00")

    assert [r["id"] for r in client.get("/api/measurements").json()] == [later, earlier]


@pytest.mark.parametrize(("target", "status"), [(10.0, 200), (1000.0, 200), (9.99, 422)])
def test_target_on_the_sweep_ends_is_allowed(
    client: TestClient, target: float, status: int
) -> None:
    assert measure(client, add_antenna(client, target=target), "good").status_code == status


def test_upload_with_target_outside_the_sweep_is_422(client: TestClient) -> None:
    rows = [(420.0 + 5 * i, db, 0.5, 0.0) for i, db in enumerate([-1, -3, -20, -3, -1])]

    response = upload(client, add_antenna(client, target=500.0), csv_text(rows).encode())

    assert response.status_code == 422
    assert "목표" in response.json()["detail"]


@pytest.mark.parametrize(("extra", "status"), [(0, 200), (1, 413)])
def test_upload_limit_is_exactly_2_mb(client: TestClient, extra: int, status: int) -> None:
    rows = [(420.0 + 5 * i, db, 0.5, 0.0) for i, db in enumerate([-1, -3, -20, -3, -1])]
    body = csv_text(rows).encode()
    padding = MB2 - len(body) + extra
    blank_line = b" " * 999 + b"\n"  # short blank lines; one huge field would hit csv's limit
    data = body + blank_line * (padding // len(blank_line)) + b" " * (padding % len(blank_line))
    assert len(data) == MB2 + extra

    assert upload(client, add_antenna(client, target=430.0), data).status_code == status


def test_measured_at_is_local_time_in_seconds(client: TestClient) -> None:
    got = measure(client, add_antenna(client), "good").json()["measured_at"]

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", got)
    assert abs((datetime.fromisoformat(got) - datetime.now()).total_seconds()) < 5


def test_non_finite_stored_numbers_go_out_as_null(client: TestClient, db: Path) -> None:
    sweep_json = "[[400000000.0, -1.0, null, null], [410000000.0, Infinity, null, null]]"
    mid = insert_row(db, add_antenna(client), "2026-11-22T12:00:00",
                     bandwidth_pct=math.inf, sweep_json=sweep_json)  # fmt: skip

    listed = client.get("/api/measurements")
    one = client.get(f"/api/measurements/{mid}")

    assert listed.status_code == one.status_code == 200
    assert listed.json()[0]["bandwidth_pct"] is None
    assert one.json()["sweep"][1]["s11_db"] is None
    assert not re.search("NaN|Infinity", listed.text + one.text)


def test_stage_filter_finds_invalid(client: TestClient) -> None:
    mid = measure(client, add_antenna(client), "positive").json()["id"]

    assert [r["id"] for r in client.get("/api/measurements?stage=invalid").json()] == [mid]


def test_stored_source_runs_through_the_service(client: TestClient, db: Path) -> None:
    antenna_id = add_antenna(client)
    first = measure(client, antenna_id, "good").json()
    request = service.MeasureInput(antenna_id=antenna_id, cal_mode="vna", change_note="")

    again = service.measure(db, StoredSource(db, first["id"]), request)

    assert again["source"] == "stored"
    assert again["card"] == first["card"]
    assert again["sweep"] == first["sweep"]
    with pytest.raises(service.NotFoundError):
        service.measure(db, StoredSource(db, 999), request)


def test_stored_sweep_that_breaks_the_rules_is_rejected(client: TestClient, db: Path) -> None:
    antenna_id = add_antenna(client, target=405.0)
    two_points = "[[400000000.0, -1.0, null, null], [410000000.0, -20.0, null, null]]"
    bad = insert_row(db, antenna_id, "2026-11-22T12:00:00", sweep_json=two_points)
    request = service.MeasureInput(antenna_id=antenna_id, cal_mode="vna", change_note="")

    with pytest.raises(service.InputError, match="3점 이상"):
        service.measure(db, StoredSource(db, bad), request)


@pytest.mark.parametrize(
    ("method", "path", "body", "status"),
    [
        ("post", "/api/measurements", {"antenna_id": 999, "source": "synthetic",
                                       "sample": "good", "cal_mode": "vna"}, 404),
        ("get", "/api/measurements/999", None, 404),
        ("get", "/api/measurements?limit=0", None, 422),
        ("get", "/api/measurements?stage=bad", None, 422),
        ("get", "/api/measurements?limit=x", None, 422),
        ("post", "/api/measurements", {"antenna_id": 1, "source": "radio",
                                       "sample": "good", "cal_mode": "vna"}, 422),
    ],
)  # fmt: skip
def test_every_error_has_a_korean_message(
    client: TestClient, method: str, path: str, body: dict[str, Any] | None, status: int
) -> None:
    add_antenna(client)
    response = client.request(method, path, json=body)

    assert response.status_code == status
    assert HANGUL.search(response.json()["detail"])


def test_error_status_follows_subclasses() -> None:
    class Narrower(service.InputError):
        pass

    assert api.status_for(Narrower("x")) == 422
    assert api.status_for(service.NotFoundError("x")) == 404
    assert api.status_for(service.TooLargeError("x")) == 413


def test_sample_sweep_survives_the_hz_round_trip() -> None:
    sweep = make_sample("offtarget_low").sweep

    assert store.sweep_from_json(store.sweep_to_json(sweep)) == sweep
