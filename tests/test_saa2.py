"""SAA-2 USB protocol against a fake serial port. No hardware needed."""

import itertools
import json
import math
import struct
from dataclasses import dataclass, field

import pytest

from src import saa2, store
from src.models import Sweep

IDENTIFY = bytes(8) + b"\x0d"
RANGE_2000_3000_201 = [
    bytes.fromhex("23 00 00 94 35 77 00 00 00 00"),
    bytes.fromhex("23 10 40 4b 4c 00 00 00 00 00"),
    bytes.fromhex("21 20 c9 00"),
    bytes.fromhex("21 22 01 00"),
    bytes.fromhex("20 30 00"),
]
REFERENCE = complex(1_000_000, -250_000)


def packet(index: int, gamma: complex, reference: complex = REFERENCE) -> bytes:
    s11 = gamma * reference
    values = (reference.real, reference.imag, s11.real, s11.imag, 7, -7)
    return struct.pack("<6iH", *(round(v) for v in values), index) + bytes(6)


def dip(index: int) -> complex:
    """A made-up reflection with its deepest point at index 89 (2445 MHz on 2000~3000/201)."""
    return complex(0.9 - 0.85 * math.exp(-(((index - 89) / 6) ** 2)), 0.1)


@dataclass
class FakeClock:
    t: float = 0.0
    sleeps: list[float] = field(default_factory=list)

    def now(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += seconds


@dataclass
class FakePort:
    """Answers like the device: '2' to identify, queued packets to each FIFO read, `screen`
    to a screenshot request."""

    clock: FakeClock
    packets: list[bytes] = field(default_factory=list)
    identity: bytes = b"2"
    writes: list[bytes] = field(default_factory=list)
    closed: bool = False
    out: bytearray = field(default_factory=bytearray)
    screen: bytes = b""

    def reset_input_buffer(self) -> None:
        self.out.clear()

    def write(self, data: bytes) -> int:
        self.writes.append(bytes(data))
        if data == IDENTIFY:
            self.out += self.identity
        elif data == b"\x20\xee\x00":
            self.out += self.screen
        elif data[:2] == b"\x18\x30":
            taken, self.packets = self.packets[: data[2]], self.packets[data[2] :]
            self.out += b"".join(taken)
        return len(data)

    def read(self, size: int) -> bytes:
        if not self.out:
            self.clock.t += 0.5  # what a read timeout costs on the real port
            return b""
        data, self.out = bytes(self.out[:size]), self.out[size:]
        return data

    def close(self) -> None:
        self.closed = True


def run(port: FakePort, start: float = 2000, stop: float = 3000, points: int = 201) -> Sweep:
    source = saa2.Saa2Source(
        "/dev/fake", saa2.make_range(start, stop, points), lambda name: port, port.clock
    )
    return source.read()


def full_port(points: int = 201) -> FakePort:
    clock = FakeClock()
    return FakePort(clock, [packet(i, dip(i)) for i in reversed(range(points))])


def test_range_commands_match_the_spec() -> None:
    port = full_port()
    run(port)
    assert port.writes[0] == IDENTIFY
    assert port.writes[1:6] == RANGE_2000_3000_201
    assert port.clock.sleeps == [0.5]


def test_normal_read_returns_s11_by_index() -> None:
    port = full_port()
    sweep = run(port)
    assert port.closed
    assert len(sweep.f_mhz) == 201
    assert (sweep.f_mhz[0], sweep.f_mhz[89], sweep.f_mhz[-1]) == (2000.0, 2445.0, 3000.0)
    assert sweep.gamma is not None
    assert sweep.gamma[89] == pytest.approx(dip(89), abs=1e-6)
    assert sweep.s11_db[89] == pytest.approx(20 * math.log10(abs(dip(89))), abs=1e-4)
    assert min(range(201), key=lambda i: sweep.s11_db[i]) == 89


def test_reads_in_batches_of_at_most_255() -> None:
    port = full_port(291)
    sweep = run(port, 2000, 3000, 291)
    counts = [w[2] for w in port.writes if w[:2] == b"\x18\x30"]
    assert all(1 <= n <= 255 for n in counts)
    assert len(sweep.f_mhz) == 291


def test_writes_only_the_range_and_fifo_registers() -> None:
    port = full_port()
    run(port)
    allowed = {IDENTIFY[:1], b"\x23\x00", b"\x23\x10", b"\x21\x20", b"\x21\x22", b"\x20\x30",
               b"\x18\x30"}  # fmt: skip
    assert all(w[:2] in allowed or w == IDENTIFY for w in port.writes)


def test_identify_failure_stops_before_any_register_write() -> None:
    port = full_port()
    port.identity = b"1"
    with pytest.raises(saa2.DeviceError):
        run(port)
    assert port.closed
    assert port.writes == [IDENTIFY]


def test_silent_device_fails_identify_within_3_seconds() -> None:
    port = full_port()
    port.identity = b""
    with pytest.raises(saa2.DeviceError):
        run(port)
    assert port.closed
    assert port.clock.t <= 3.5


def test_index_out_of_range_is_an_error() -> None:
    port = full_port()
    port.packets[0] = packet(201, 0.5 + 0j)
    with pytest.raises(saa2.DeviceError):
        run(port)
    assert port.closed


def test_zero_reference_is_an_error() -> None:
    port = full_port()
    port.packets[3] = packet(5, 0.5 + 0j, reference=0j)
    with pytest.raises(saa2.DeviceError):
        run(port)
    assert port.closed


def test_missing_points_time_out_after_40_seconds() -> None:
    port = full_port()
    del port.packets[100]
    with pytest.raises(saa2.DeviceError):
        run(port)
    assert port.closed
    assert 40 <= port.clock.t <= 41


@dataclass
class DyingPort(FakePort):
    """Answers identify, then the cable is pulled: the next write raises like pyserial does."""

    def write(self, data: bytes) -> int:
        if self.writes:
            self.writes.append(bytes(data))
            raise saa2.serial.SerialTimeoutException("Write timeout")
        return super().write(data)


def test_serial_error_mid_measurement_is_a_device_error_and_closes_the_port() -> None:
    port = DyingPort(FakeClock())
    with pytest.raises(saa2.DeviceError, match="[가-힣]"):
        run(port)
    assert port.closed


def test_open_serial_uses_the_spec_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    monkeypatch.setattr(saa2.serial, "Serial", lambda *a, **k: calls.append((a, k)) or "port")
    assert saa2.open_serial("/dev/cu.usbmodem1") == "port"
    assert calls == [(("/dev/cu.usbmodem1", 115200), {"timeout": 0.5, "write_timeout": 2.0})]


def test_open_serial_failure_is_a_device_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> None:
        raise saa2.serial.SerialException("could not open port")

    monkeypatch.setattr(saa2.serial, "Serial", refuse)
    with pytest.raises(saa2.DeviceError, match="[가-힣]"):
        saa2.open_serial("/dev/none")


def test_open_failure_is_a_device_error() -> None:
    def broken(name: str) -> FakePort:
        raise saa2.DeviceError("없는 포트")

    source = saa2.Saa2Source("/dev/none", saa2.make_range(2000, 3000, 201), broken, FakeClock())
    with pytest.raises(saa2.DeviceError):
        source.read()


@pytest.mark.parametrize(
    ("start", "stop", "points"),
    [
        (2000, 3000, 201),
        (0.05, 3000, 1001),
        (433.3, 433.9, 11),
        (2000, 3000, 291),
        (1.234567, 2.5, 13),
    ],
)
def test_axis_is_integer_hz_and_survives_storage(start: float, stop: float, points: int) -> None:
    port = full_port(points)
    sweep = run(port, start, stop, points)
    axis = saa2.axis_hz(saa2.make_range(start, stop, points))
    assert all(isinstance(hz, int) for hz in axis)
    assert sweep.f_mhz == tuple(hz / 1e6 for hz in axis)
    stored = store.sweep_to_json(sweep)
    assert [round(p[0]) for p in json.loads(stored)] == list(axis)
    assert store.sweep_from_json(stored) == sweep


def test_axis_steps_match_what_the_device_was_told() -> None:
    sweep_range = saa2.make_range(2000, 3000, 291)
    axis = saa2.axis_hz(sweep_range)
    assert axis[0] == 2_000_000_000
    assert all(b - a == sweep_range.step_hz for a, b in itertools.pairwise(axis))


@pytest.mark.parametrize(
    ("start", "stop", "points"),
    [(2000, 3000, 291), (2000, 3000, 13), (0.05, 3000, 1001), (2000, 3000, 202), (100, 101, 1001)],
)
def test_step_rounds_down_so_the_last_point_stays_within_the_stop(
    start: float, stop: float, points: int
) -> None:
    sweep_range = saa2.make_range(start, stop, points)
    last = saa2.axis_hz(sweep_range)[-1]
    assert last <= sweep_range.stop_hz <= saa2.MAX_HZ
    assert sweep_range.stop_hz - last < points
    assert sweep_range.step_hz == (sweep_range.stop_hz - sweep_range.start_hz) // (points - 1)


def test_291_points_up_to_3_ghz_is_accepted() -> None:
    """The measured 291-point case: a rounded step would end 40 Hz above 3 GHz."""
    assert saa2.axis_hz(saa2.make_range(2000, 3000, 291))[-1] == 2_999_999_750


@pytest.mark.parametrize(
    ("start", "stop", "points"),
    [
        (3000, 2000, 201),
        (2000, 2000, 201),
        (0.049, 100, 201),
        (0.0499999, 100, 201),
        (2000, 3000.001, 201),
        (2000, 3000.0000001, 201),
        (2000, 1e308, 201),
        (-1e308, 3000, 201),
        (2000, 3000, 10),
        (2000, 3000, 1002),
        (math.nan, 3000, 201),
        (2000, math.inf, 201),
    ],
)
def test_bad_range_is_rejected(start: float, stop: float, points: int) -> None:
    with pytest.raises(ValueError, match="[가-힣]"):
        saa2.make_range(start, stop, points)


def test_range_edges_are_accepted() -> None:
    assert saa2.make_range(0.05, 3000, 11).start_hz == 50_000
    assert saa2.make_range(0.05, 3000, 1001).stop_hz == 3_000_000_000


@dataclass
class PortInfo:
    device: str
    vid: int | None
    pid: int | None


def test_saa2_ports_come_first() -> None:
    infos = [
        PortInfo("/dev/cu.Bluetooth", None, None),
        PortInfo("/dev/cu.other", 0x04B4, 9),
        PortInfo("/dev/cu.usbmodem1", 0x04B4, 8),
    ]
    assert saa2.order_ports(infos) == ["/dev/cu.usbmodem1", "/dev/cu.Bluetooth", "/dev/cu.other"]
