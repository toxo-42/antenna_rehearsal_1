"""SAA-2 screenshot to PNG, with a fake port, and `GET /api/device/screen`."""

import struct
import threading
import zlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src import saa2, saa2_screen
from tests.test_saa2 import IDENTIFY, DyingPort, FakeClock, FakePort

RED, GREEN, BLUE, WHITE = 0xF800, 0x07E0, 0x001F, 0xFFFF


def screen_bytes(width: int, height: int, pixels: list[int], bits: int = 16) -> bytes:
    body = b"".join(p.to_bytes(2, "big") for p in pixels)
    return struct.pack("<HHB", width, height, bits) + body


def png_pixels(png: bytes) -> tuple[int, int, list[tuple[int, int, int]]]:
    """Width, height and RGB pixels of an 8-bit RGB PNG with filter 0 rows."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height, depth, color = struct.unpack(">IIBB", png[16:26])
    assert (depth, color) == (8, 2)
    idat = png.index(b"IDAT")
    size = struct.unpack(">I", png[idat - 4 : idat])[0]
    raw = zlib.decompress(png[idat + 4 : idat + 4 + size])
    stride = 1 + width * 3
    rows = [raw[y * stride : (y + 1) * stride] for y in range(height)]
    assert all(row[0] == 0 for row in rows)
    pixels = [tuple(row[1 + 3 * x : 4 + 3 * x]) for row in rows for x in range(width)]
    return width, height, pixels  # type: ignore[return-value]


def capture(port: FakePort) -> bytes:
    return saa2_screen.capture_png("/dev/fake", lambda name: port, port.clock)


def test_screen_becomes_a_png_with_the_same_colors() -> None:
    port = FakePort(FakeClock(), screen=screen_bytes(2, 2, [RED, GREEN, BLUE, WHITE]))
    width, height, pixels = png_pixels(capture(port))
    assert (width, height) == (2, 2)
    assert pixels == [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
    assert port.closed


def test_pixels_are_big_endian_like_the_real_device() -> None:
    """Bytes seen on a real SAA-2 measure screen (2026-11-22): `ff e0` is the yellow CH0 trace
    and `84 10` the gray grid."""
    header = struct.pack("<HHB", 2, 1, 16)
    port = FakePort(FakeClock(), screen=header + bytes.fromhex("ffe0 8410"))
    assert png_pixels(capture(port))[2] == [(255, 255, 0), (131, 129, 131)]


def test_screen_only_identifies_and_asks_for_the_screen() -> None:
    port = FakePort(FakeClock(), screen=screen_bytes(1, 1, [WHITE]))
    capture(port)
    assert port.writes == [IDENTIFY, b"\x20\xee\x00"]


def test_full_size_screen() -> None:
    port = FakePort(FakeClock(), screen=screen_bytes(320, 240, [BLUE] * 320 * 240))
    width, height, pixels = png_pixels(capture(port))
    assert (width, height, set(pixels)) == (320, 240, {(0, 0, 255)})


@pytest.mark.parametrize(
    "screen",
    [
        b"",
        screen_bytes(2, 2, [RED] * 4, bits=24),
        screen_bytes(2, 2, [RED] * 4)[:-1],
        screen_bytes(0, 240, []),
        screen_bytes(2000, 2000, []),
    ],
)
def test_bad_screen_is_a_device_error(screen: bytes) -> None:
    port = FakePort(FakeClock(), screen=screen)
    with pytest.raises(saa2.DeviceError):
        capture(port)
    assert port.closed


def test_serial_error_during_screen_is_a_device_error_and_closes_the_port() -> None:
    port = DyingPort(FakeClock())
    with pytest.raises(saa2.DeviceError, match="[가-힣]"):
        capture(port)
    assert port.closed


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "t.db"))


def test_screen_route_returns_png(client: TestClient) -> None:
    port = FakePort(FakeClock(), screen=screen_bytes(1, 1, [GREEN]))
    client.app.state.serial_opener = lambda name: port  # type: ignore[attr-defined]
    response = client.get("/api/device/screen", params={"port": "/dev/fake"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert png_pixels(response.content)[2] == [(0, 255, 0)]


def test_screen_route_errors(client: TestClient) -> None:
    port = FakePort(FakeClock(), identity=b"0")
    client.app.state.serial_opener = lambda name: port  # type: ignore[attr-defined]
    assert client.get("/api/device/screen", params={"port": "/dev/fake"}).status_code == 503
    assert client.get("/api/device/screen", params={"port": " "}).status_code == 422
    assert client.get("/api/device/screen").status_code == 422


def test_screen_route_waits_for_no_one_while_measuring(client: TestClient) -> None:
    lock: threading.Lock = client.app.state.usb_lock  # type: ignore[attr-defined]
    with lock:
        response = client.get("/api/device/screen", params={"port": "/dev/fake"})
    assert response.status_code == 409
