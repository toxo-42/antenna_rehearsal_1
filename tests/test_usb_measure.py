"""USB measurement through service and HTTP, with a fake SAA-2 port."""

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src import api, saa2, service
from src.models import CalMode, Sweep
from src.verdict import CAL_TEXT
from tests.test_saa2 import FakeClock, FakePort, dip, full_port, packet, run


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "t.db"))


def add_patch(client: TestClient, target: float = 2450.0) -> int:
    body = {"name": "p", "kind": "patch", "target_mhz": target}
    return client.post("/api/antennas", json=body).json()["id"]


def use_port(client: TestClient, port: FakePort) -> list[str]:
    """Plug a fake device in; returns the names it was opened with."""
    opened: list[str] = []

    def opener(name: str) -> FakePort:
        opened.append(name)
        return port

    client.app.state.serial_opener = opener  # type: ignore[attr-defined]
    return opened


def usb_body(antenna_id: int, **change: Any) -> dict[str, Any]:
    body = {"antenna_id": antenna_id, "source": "usb", "port": "/dev/fake", "start_mhz": 2000.0,
            "stop_mhz": 3000.0, "points": 201, "cal_mode": "vna", "change_note": ""}  # fmt: skip
    return body | change


def test_usb_measurement_is_saved_as_uncalibrated(client: TestClient) -> None:
    port = full_port()
    opened = use_port(client, port)
    response = client.post("/api/measurements", json=usb_body(add_patch(client)))
    assert response.status_code == 200, response.text
    data = response.json()
    assert opened == ["/dev/fake"]
    assert (data["source"], data["cal_mode"]) == ("usb", "unknown")
    assert len(data["sweep"]) == 201
    assert data["resonance_mhz"] == pytest.approx(2445, abs=10)
    assert client.get(f"/api/measurements/{data['id']}").json() == data


@pytest.mark.parametrize(
    "change",
    [
        {"port": None},
        {"port": " "},
        {"start_mhz": None},
        {"points": None},
        {"start_mhz": 3000.0, "stop_mhz": 2000.0},
        {"start_mhz": 0.01},
        {"stop_mhz": 3500.0},
        {"points": 10},
        {"points": 1002},
        {"start_mhz": 2500.0},
        {"cal_mode": "auto"},
    ],
)
def test_bad_usb_request_is_422_without_touching_the_device(
    client: TestClient, change: dict[str, Any]
) -> None:
    opened = use_port(client, full_port())
    response = client.post("/api/measurements", json=usb_body(add_patch(client), **change))
    assert response.status_code == 422
    assert any("가" <= ch <= "힣" for ch in response.json()["detail"])
    assert opened == []


def test_target_beyond_the_last_programmed_point_is_422_before_the_device(
    client: TestClient,
) -> None:
    """2000~3000 MHz in 13 points ends at 2999.999996 MHz, so a 3000 MHz target is outside."""
    opened = use_port(client, full_port(13))
    body = usb_body(add_patch(client, target=3000.0), points=13)
    response = client.post("/api/measurements", json=body)
    assert response.status_code == 422
    assert opened == []


@dataclass
class UsbSweep:
    """Any sweep that claims to come over USB, whatever path saves it."""

    sweep: Sweep
    source: str = "usb"

    def read(self) -> Sweep:
        return self.sweep


def test_every_usb_save_path_stores_unknown_calibration(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    create_app(db)
    antenna = service.create_antenna(db, service.AntennaInput("p", "patch", 2450.0))
    sweep = run(full_port())
    request = service.MeasureInput(antenna["id"], "vna", "")
    saved = service.measure(db, UsbSweep(sweep), request)
    assert saved["cal_mode"] == "unknown"
    card_text = json.dumps(saved["card"], ensure_ascii=False)
    assert CAL_TEXT[CalMode.UNKNOWN] in card_text
    assert CAL_TEXT[CalMode.VNA] not in card_text


@pytest.mark.parametrize(
    ("source", "asked", "stored"),
    [
        ("usb", "vna", "unknown"),
        ("usb", "unknown", "unknown"),
        ("csv", "vna", "vna"),
        ("synthetic", "vna", "vna"),
        ("stored", "unknown", "unknown"),
    ],
)
def test_stored_cal_mode(source: str, asked: str, stored: str) -> None:
    assert service.stored_cal_mode(source, asked) == stored


@pytest.mark.parametrize("broken", ["identity", "index", "reference"])
def test_device_error_is_503_and_saves_nothing(client: TestClient, broken: str) -> None:
    port = full_port()
    if broken == "identity":
        port.identity = b"0"
    elif broken == "index":
        port.packets[0] = packet(999, 0.5 + 0j)
    else:
        port.packets[0] = packet(200, 0.5 + 0j, reference=0j)
    use_port(client, port)
    antenna_id = add_patch(client)
    response = client.post("/api/measurements", json=usb_body(antenna_id))
    assert response.status_code == 503
    assert any("가" <= ch <= "힣" for ch in response.json()["detail"])
    assert port.closed
    assert client.get(f"/api/measurements?antenna_id={antenna_id}").json() == []


def test_values_out_of_the_allowed_range_are_422(client: TestClient) -> None:
    port = full_port()
    port.packets[5] = packet(195, 5000 + 0j, reference=100 + 0j)  # S11_real past ±1000
    use_port(client, port)
    response = client.post("/api/measurements", json=usb_body(add_patch(client)))
    assert response.status_code == 422
    assert port.closed


def test_busy_and_device_errors_map_to_409_and_503() -> None:
    assert api.status_for(service.BusyError("x")) == 409
    assert api.status_for(service.DeviceError("x")) == 503


def test_ports_list(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(saa2, "list_ports", lambda: ["/dev/cu.usbmodem1", "/dev/cu.x"])
    assert client.get("/api/ports").json() == ["/dev/cu.usbmodem1", "/dev/cu.x"]


def test_second_usb_measurement_while_one_runs_is_busy(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    create_app(db)
    antenna = service.create_antenna(db, service.AntennaInput("p", "patch", 2450.0))
    started, release = threading.Event(), threading.Event()
    clock = FakeClock()

    def slow_opener(name: str) -> FakePort:
        started.set()
        release.wait(5)
        return FakePort(clock, [packet(i, dip(i)) for i in range(201)])

    lock = threading.Lock()
    request = service.MeasureInput(antenna["id"], "unknown", "")

    def source(opener: saa2.Opener) -> saa2.Saa2Source:
        return saa2.Saa2Source("/dev/fake", saa2.make_range(2000, 3000, 201), opener, clock)

    first: list[Any] = []
    worker = threading.Thread(
        target=lambda: first.append(service.measure_usb(db, source(slow_opener), request, lock))
    )
    worker.start()
    assert started.wait(5)
    with pytest.raises(service.BusyError):
        service.measure_usb(db, source(slow_opener), request, lock)
    release.set()
    worker.join(5)
    assert first and first[0]["source"] == "usb"
    assert not lock.locked()
