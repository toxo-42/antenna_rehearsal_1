"""Device edges: the antenna deleted mid-measurement, and port errors that are not OSError."""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src import saa2, saa2_screen
from tests.test_saa2 import FakeClock, FakePort, full_port
from tests.test_usb_measure import add_patch, usb_body, use_port


class TermiosError(Exception):
    """Stands in for `termios.error`, which is not an OSError (and is missing on Windows)."""


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


def korean(response: Any) -> bool:
    return any("가" <= c <= "힣" for c in response.json()["detail"])


@dataclass
class BrokenPort(FakePort):
    """Raises a non-OSError at one step: reset, write, read or close."""

    step: str = "write"
    calls: list[str] = field(default_factory=list)

    def _maybe(self, step: str) -> None:
        self.calls.append(step)
        if step == self.step:
            raise TermiosError(5, "Input/output error")

    def reset_input_buffer(self) -> None:
        self._maybe("reset")
        super().reset_input_buffer()

    def write(self, data: bytes) -> int:
        self._maybe("write")
        return super().write(data)

    def read(self, size: int) -> bytes:
        self._maybe("read")
        return super().read(size)

    def close(self) -> None:
        super().close()
        self._maybe("close")


def broken(step: str) -> BrokenPort:
    good = full_port()
    return BrokenPort(good.clock, good.packets, step=step)


def test_the_antenna_deleted_during_a_usb_measurement_is_a_404(
    client: TestClient, db: Path
) -> None:
    antenna_id = add_patch(client)
    port = full_port()
    deleted: list[int] = []

    def delete_then_reset() -> None:
        deleted.append(client.delete(f"/api/antennas/{antenna_id}").status_code)

    port.reset_input_buffer = delete_then_reset  # type: ignore[method-assign]
    use_port(client, port)

    response = client.post("/api/measurements", json=usb_body(antenna_id))

    assert deleted == [200]
    assert response.status_code == 404, response.text
    assert korean(response)
    assert counts(db) == (0, 0)
    assert port.closed
    assert not client.app.state.usb_lock.locked()  # type: ignore[attr-defined]


@pytest.mark.parametrize("step", ["reset", "write", "read", "close"])
def test_any_port_error_during_a_measurement_is_a_503(
    step: str, client: TestClient, db: Path
) -> None:
    port = broken(step)
    use_port(client, port)

    response = client.post("/api/measurements", json=usb_body(add_patch(client)))

    assert response.status_code == 503, response.text
    assert korean(response)
    assert port.closed
    assert counts(db) == (1, 0)
    assert not client.app.state.usb_lock.locked()  # type: ignore[attr-defined]


def test_an_opener_that_raises_something_else_is_a_503(client: TestClient, db: Path) -> None:
    def opener(name: str) -> FakePort:
        raise TermiosError(6, "Device not configured")

    client.app.state.serial_opener = opener  # type: ignore[attr-defined]
    antenna_id = add_patch(client)

    measured = client.post("/api/measurements", json=usb_body(antenna_id))
    screen = client.get("/api/device/screen", params={"port": "/dev/fake"})

    assert (measured.status_code, screen.status_code) == (503, 503)
    assert korean(measured) and korean(screen)
    assert counts(db) == (1, 0)
    assert not client.app.state.usb_lock.locked()  # type: ignore[attr-defined]


@pytest.mark.parametrize("step", ["reset", "write", "read", "close"])
def test_any_port_error_during_a_screenshot_is_a_503(step: str, client: TestClient) -> None:
    port = BrokenPort(FakeClock(), screen=b"\x01\x00\x01\x00\x10\x07\xe0", step=step)
    client.app.state.serial_opener = lambda name: port  # type: ignore[attr-defined]

    response = client.get("/api/device/screen", params={"port": "/dev/fake"})

    assert response.status_code == 503, response.text
    assert korean(response)
    assert port.closed
    assert not client.app.state.usb_lock.locked()  # type: ignore[attr-defined]


def test_a_device_error_keeps_its_own_message() -> None:
    port = FakePort(FakeClock(), identity=b"0")

    with pytest.raises(saa2.DeviceError, match="응답하지 않습니다"):
        saa2_screen.capture_png("/dev/fake", lambda name: port, port.clock)
    assert port.closed


def test_open_serial_turns_any_open_failure_into_a_device_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise TermiosError(22, "Invalid argument")

    monkeypatch.setattr(saa2.serial, "Serial", refuse)

    with pytest.raises(saa2.DeviceError, match="열 수 없습니다"):
        saa2.open_serial("/dev/fake")
