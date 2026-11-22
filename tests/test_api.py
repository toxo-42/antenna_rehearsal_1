"""HTTP API over a temporary database: antennas, samples, measurements, uploads, errors."""

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src.classify import classify
from src.models import Antenna, CalMode, Sweep
from src.sources import StoredSource
from src.synthetic import SAMPLE_NAMES, make_sample
from src.verdict import build_card

CONTRACT = Path(__file__).resolve().parent.parent / "contract" / "measurement.json"
UPLOAD = "/api/measurements/upload"
RESONANCE_KEYS = ("resonance_mhz", "s11_db", "bandwidth_pct")


@pytest.fixture
def db(tmp_path: Path) -> Path:
    return tmp_path / "t.db"


@pytest.fixture
def client(db: Path) -> TestClient:
    return TestClient(create_app(db))


def add_antenna(client: TestClient, kind: str = "monopole", target: float = 433.0) -> int:
    response = client.post("/api/antennas", json={"name": "a", "kind": kind, "target_mhz": target})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def measure(client: TestClient, antenna_id: int, sample: str, cal_mode: str = "vna") -> Any:
    body = {"antenna_id": antenna_id, "source": "synthetic", "sample": sample,
            "cal_mode": cal_mode, "change_note": ""}  # fmt: skip
    return client.post("/api/measurements", json=body)


def csv_text(rows: list[tuple[float, float, float, float]]) -> str:
    lines = ["Frequency_Hz,S11_dB,S11_real,S11_imag"]
    lines += [f"{f_mhz * 1e6},{db},{re},{im}" for f_mhz, db, re, im in rows]
    return "\n".join(lines) + "\n"


def upload(client: TestClient, antenna_id: int, data: bytes) -> Any:
    form = {"antenna_id": str(antenna_id), "cal_mode": "vna", "change_note": "첫 측정"}
    return client.post(UPLOAD, files={"file": ("s.csv", data, "text/csv")}, data=form)


def card_dict(card: object) -> Any:
    return json.loads(json.dumps(asdict(card), ensure_ascii=False))  # type: ignore[call-overload]


def core_resonance(sweep: Sweep, antenna: Antenna) -> dict[str, float | None]:
    """The three resonance numbers the judging core picks, independent of the API."""
    selected = classify(sweep, antenna).selected
    if selected is None:
        return dict.fromkeys(RESONANCE_KEYS)
    return dict(zip(RESONANCE_KEYS, (selected.f_mhz, selected.s11_db, selected.bandwidth_pct)))


def card_strings(card: dict[str, Any]) -> list[str]:
    texts = [card["stage"], card["headline"], *card["status"]]
    return texts + [value for d in card["diagnoses"] for value in d.values()]


def non_finite_words(card: dict[str, Any]) -> list[str]:
    """Strings with Python's `inf`/`nan` spelling as a word (not inside `resonance`)."""
    pattern = re.compile(r"(?<![a-z])(inf|nan)(?![a-z])", re.IGNORECASE)
    return [text for text in card_strings(card) if pattern.search(text)]


def assert_same_shape(expected: Any, actual: Any, path: str = "") -> None:
    """Same keys at every level and same value types; int and float count as one type."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict) and set(actual) == set(expected), path
        for key in expected:
            assert_same_shape(expected[key], actual[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list), path
        for index, item in enumerate(actual):
            assert_same_shape(expected[0], item, f"{path}[{index}]")
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert isinstance(actual, (int, float)) and not isinstance(actual, bool), path
    else:
        assert type(actual) is type(expected), path


def test_antennas_are_created_and_listed(client: TestClient) -> None:
    antenna_id = add_antenna(client, "patch", 915.0)

    assert client.get("/api/antennas").json() == [
        {"id": antenna_id, "name": "a", "kind": "patch", "target_mhz": 915.0}
    ]


def test_samples_list_name_kind_and_target(client: TestClient) -> None:
    samples = client.get("/api/samples").json()

    assert [s["name"] for s in samples] == list(SAMPLE_NAMES)
    assert samples[0] == {"name": "good", "kind": "monopole", "target_mhz": 433.0}
    assert {"name": "patch_good", "kind": "patch", "target_mhz": 433.0} in samples


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_stored_card_matches_the_core_and_the_stored_sweep(
    client: TestClient, db: Path, name: str
) -> None:
    sample = make_sample(name)
    antenna_id = add_antenna(client, sample.antenna.kind.value, sample.antenna.target_mhz)
    created = measure(client, antenna_id, name)
    assert created.status_code == 200, created.text

    got = client.get(f"/api/measurements/{created.json()['id']}").json()
    antenna = Antenna(name="a", kind=sample.antenna.kind, target_mhz=sample.antenna.target_mhz)
    direct = card_dict(build_card(sample.sweep, antenna, CalMode.VNA))
    reread = card_dict(build_card(StoredSource(db, got["id"]).read(), antenna, CalMode.VNA))

    row = client.get(f"/api/measurements?antenna_id={antenna_id}").json()[0]
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    core = core_resonance(sample.sweep, antenna)
    contract.update({key: None for key, value in core.items() if value is None})

    assert {key: got[key] for key in RESONANCE_KEYS} == {key: row[key] for key in RESONANCE_KEYS}
    assert got == created.json()
    assert got["card"] == direct
    assert reread == direct
    assert_same_shape(contract, got)
    assert got["source"] == "synthetic"
    assert len(got["sweep"]) == len(sample.sweep.f_mhz)
    assert non_finite_words(got["card"]) == []


def test_measurement_has_server_time_and_stored_columns(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    got = measure(client, antenna_id, "offtarget_low").json()
    row = client.get("/api/measurements").json()[0]

    assert len(got["measured_at"]) == len("2026-11-26T15:00:00")
    assert got["antenna"] == {
        "id": antenna_id,
        "name": "a",
        "kind": "monopole",
        "target_mhz": 433.0,
    }
    first_db = make_sample("offtarget_low").sweep.s11_db[0]
    assert got["sweep"][0] == {"f_mhz": 10.0, "s11_db": first_db}
    assert row["stage"] == "offtarget"
    assert row["resonance_mhz"] == pytest.approx(381.25, abs=0.005)
    assert row["bandwidth_pct"] == pytest.approx(13.89, abs=0.005)
    assert "sweep_json" not in row and "card_json" not in row
    assert {key: got[key] for key in RESONANCE_KEYS} == {key: row[key] for key in RESONANCE_KEYS}


def test_no_selected_resonance_stores_nulls(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    created = measure(client, antenna_id, "open").json()

    row = client.get("/api/measurements").json()[0]
    got = client.get(f"/api/measurements/{row['id']}").json()

    assert (row["resonance_mhz"], row["s11_db"], row["bandwidth_pct"]) == (None, None, None)
    assert [got[key] for key in RESONANCE_KEYS] == [created[key] for key in RESONANCE_KEYS]
    assert [got[key] for key in RESONANCE_KEYS] == [None, None, None]


def test_list_filters_orders_and_pages(client: TestClient) -> None:
    a, b = add_antenna(client), add_antenna(client)
    ids = [measure(client, a, "good").json()["id"], measure(client, a, "open").json()["id"]]
    ids.append(measure(client, b, "good").json()["id"])

    assert [r["id"] for r in client.get("/api/measurements").json()] == ids[::-1]
    assert [r["id"] for r in client.get(f"/api/measurements?antenna_id={a}").json()] == ids[1::-1]
    assert [r["id"] for r in client.get("/api/measurements?stage=none").json()] == [ids[1]]
    paged = client.get("/api/measurements?limit=1&offset=1").json()
    assert [r["id"] for r in paged] == [ids[1]]


def test_history_survives_an_app_restart(db: Path) -> None:
    first = TestClient(create_app(db))
    mid = measure(first, add_antenna(first), "good").json()["id"]

    second = TestClient(create_app(db))

    assert [r["id"] for r in second.get("/api/measurements").json()] == [mid]
    assert second.get(f"/api/measurements/{mid}").status_code == 200


def test_csv_upload_is_judged_and_stored(client: TestClient) -> None:
    antenna_id = add_antenna(client, target=435.0)
    rows = [(420.0 + 5 * i, db, 0.5, 0.0) for i, db in enumerate([-1, -3, -8, -20, -8, -3, -1])]

    response = upload(client, antenna_id, ("﻿" + csv_text(rows)).encode("utf-8"))

    assert response.status_code == 200, response.text
    assert response.json()["source"] == "csv"
    assert response.json()["change_note"] == "첫 측정"
    assert client.get("/api/measurements").json()[0]["id"] == response.json()["id"]


@pytest.mark.parametrize("dip_db", [-20.0, -8.0])
def test_reflection_of_exactly_one_gives_no_rx_line_and_no_inf(
    client: TestClient, dip_db: float
) -> None:
    antenna_id = add_antenna(client, target=435.0)
    dbs = [-1.0, -2.0, -4.0, dip_db, -4.0, -2.0, -1.0]
    rows = [(420.0 + 5 * i, db, 1.0 if i == 3 else 0.5, 0.0) for i, db in enumerate(dbs)]

    response = upload(client, antenna_id, csv_text(rows).encode("utf-8"))

    assert response.status_code == 200, response.text
    card = response.json()["card"]
    assert not [line for line in card["status"] if line.startswith("공진점 R")]
    assert non_finite_words(card) == []


@pytest.mark.parametrize(
    ("data", "status"),
    [
        (b"Frequency_Hz,S11_dB\n1,2\n", 422),
        ("Frequency_Hz,S11_dB\n400e6,-1\n410e6,-20\n420e6,-1\n".encode("utf-16"), 422),
        (b"\xff\xfe\x00bad", 422),
        (b"Frequency_Hz,S11_dB\n" + b"#" * (2 * 1024 * 1024), 413),
    ],
)
def test_bad_uploads_are_rejected(client: TestClient, data: bytes, status: int) -> None:
    response = upload(client, add_antenna(client), data)

    assert response.status_code == status
    assert any("가" <= ch <= "힣" for ch in response.json()["detail"])
    assert client.get("/api/measurements").json() == []


@pytest.mark.parametrize(
    "body",
    [
        {"name": "", "kind": "monopole", "target_mhz": 433.0},
        {"name": "   ", "kind": "monopole", "target_mhz": 433.0},
        {"name": "a", "kind": "dipole", "target_mhz": 433.0},
        {"name": "a", "kind": "monopole", "target_mhz": 0},
        {"name": "a", "kind": "monopole", "target_mhz": -5},
        {"name": "a", "kind": "monopole"},
        {"name": "a", "kind": "monopole", "target_mhz": "abc"},
    ],
)
def test_bad_antenna_is_422_in_korean(client: TestClient, body: dict[str, Any]) -> None:
    response = client.post("/api/antennas", json=body)

    assert response.status_code == 422
    assert any("가" <= ch <= "힣" for ch in response.json()["detail"])


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_target_is_422(client: TestClient, raw: str) -> None:
    body = '{"name": "a", "kind": "monopole", "target_mhz": ' + raw + "}"
    headers = {"content-type": "application/json"}

    assert client.post("/api/antennas", content=body, headers=headers).status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        {"source": "csv"},
        {"source": "usb"},
        {"source": "stored"},
        {"sample": None},
        {"sample": "nope"},
        {"cal_mode": "auto"},
    ],
)
def test_bad_measurement_request_is_422(client: TestClient, change: dict[str, Any]) -> None:
    body = {"antenna_id": add_antenna(client), "source": "synthetic", "sample": "good",
            "cal_mode": "vna", "change_note": ""}  # fmt: skip

    response = client.post("/api/measurements", json=body | change)

    assert response.status_code == 422
    assert any("가" <= ch <= "힣" for ch in response.json()["detail"])
