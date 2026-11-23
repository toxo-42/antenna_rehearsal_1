"""SAA-2 (NanoVNA V2, HW V2_2, firmware 1.2) over USB serial.

The PC sets the sweep range; the device screen settings are not used. Only the four range
registers and the FIFO are written, never calibration or any other address. USB values carry no
device calibration. Errors carry a Korean message: DeviceError (device) or ValueError (input).
"""

import math
import struct
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol

import serial
from serial.tools import list_ports as serial_ports

from src.models import Sweep

BAUD = 115200
READ_TIMEOUT_S = 0.5
WRITE_TIMEOUT_S = 2.0
SAA2_VID, SAA2_PID = 0x04B4, 8
MIN_HZ, MAX_HZ = 50_000, 3_000_000_000
MIN_POINTS, MAX_POINTS = 11, 1001
HZ_PER_MHZ = 1_000_000
IDENTIFY = bytes(8) + b"\x0d"
DEVICE_ID = b"2"
IDENTIFY_S = 3.0
SETTLE_S = 0.5
COLLECT_S = 40.0
CLEAR_FIFO = b"\x20\x30\x00"
MAX_BATCH = 255
PACKET_BYTES = 32
PACKET = struct.Struct("<6iH")  # reference re/im, S11 re/im, S21 re/im, point index


class DeviceError(RuntimeError):
    """The device did not answer as expected. The port is closed and nothing is kept."""


class SerialPort(Protocol):
    def write(self, data: bytes, /) -> int | None: ...
    def read(self, size: int = 1, /) -> bytes: ...
    def reset_input_buffer(self) -> None: ...
    def close(self) -> None: ...


Opener = Callable[[str], SerialPort]


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class SystemClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class PortInfo(Protocol):
    device: str
    vid: int | None
    pid: int | None


@dataclass(frozen=True)
class SweepRange:
    """What the device is told: start, integer step and point count, all in whole Hz."""

    start_hz: int
    stop_hz: int
    points: int
    step_hz: int


def make_range(start_mhz: float, stop_mhz: float, points: int) -> SweepRange:
    """Check a requested range (50 kHz~3 GHz, start < stop, 11~1001 points).

    The step is rounded down to whole Hz, so the last point never passes the requested stop.
    """
    if not (math.isfinite(start_mhz) and math.isfinite(stop_mhz)):
        raise ValueError("시작·종료 주파수는 유한한 수여야 합니다.")
    if start_mhz >= stop_mhz:
        raise ValueError("시작 주파수가 종료 주파수보다 작아야 합니다.")
    # Checked in MHz before converting, so a huge finite value cannot overflow.
    if start_mhz < MIN_HZ / HZ_PER_MHZ or stop_mhz > MAX_HZ / HZ_PER_MHZ:
        raise ValueError("VNA 측정 범위는 0.05~3000 MHz입니다. 범위를 그 안으로 정해 주세요.")
    if not MIN_POINTS <= points <= MAX_POINTS:
        raise ValueError(f"점 개수는 {MIN_POINTS}~{MAX_POINTS}개여야 합니다 (받은 값: {points}).")
    start_hz, stop_hz = round(start_mhz * HZ_PER_MHZ), round(stop_mhz * HZ_PER_MHZ)
    step_hz = (stop_hz - start_hz) // (points - 1)
    if step_hz < 1:
        raise ValueError("범위가 점 개수에 비해 너무 좁습니다. 범위를 넓히거나 점을 줄여 주세요.")
    return SweepRange(start_hz, stop_hz, points, step_hz)


def axis_hz(sweep_range: SweepRange) -> tuple[int, ...]:
    """The frequencies the device measures: start + i * step, whole Hz, ending at or below stop."""
    return tuple(sweep_range.start_hz + i * sweep_range.step_hz for i in range(sweep_range.points))


def range_commands(sweep_range: SweepRange) -> list[bytes]:
    """Register writes for start, step, point count and one value per frequency (little endian)."""
    return [
        b"\x23\x00" + sweep_range.start_hz.to_bytes(8, "little"),
        b"\x23\x10" + sweep_range.step_hz.to_bytes(8, "little"),
        b"\x21\x20" + sweep_range.points.to_bytes(2, "little"),
        b"\x21\x22\x01\x00",
    ]


def order_ports(infos: Iterable[PortInfo]) -> list[str]:
    """Port names with SAA-2 (VID 0x04B4, PID 8) first, otherwise in the given order."""
    ports = list(infos)
    ports.sort(key=lambda p: (p.vid, p.pid) != (SAA2_VID, SAA2_PID))
    return [p.device for p in ports]


def list_ports() -> list[str]:
    return order_ports(serial_ports.comports())


def open_serial(name: str) -> SerialPort:
    try:
        return serial.Serial(name, BAUD, timeout=READ_TIMEOUT_S, write_timeout=WRITE_TIMEOUT_S)
    except (serial.SerialException, ValueError) as error:
        raise DeviceError(
            f"포트 {name}을(를) 열 수 없습니다. 케이블과 포트를 확인해 주세요. ({error})"
        ) from None


def read_until(port: SerialPort, size: int, clock: Clock, deadline: float) -> bytes:
    """Read `size` bytes, or fewer when `deadline` passes first."""
    data = bytearray()
    while len(data) < size and clock.now() < deadline:
        data += port.read(size - len(data))
    return bytes(data)


def identify(port: SerialPort, clock: Clock) -> None:
    port.reset_input_buffer()
    port.write(IDENTIFY)
    reply = read_until(port, 1, clock, clock.now() + IDENTIFY_S)
    if reply != DEVICE_ID:
        raise DeviceError(
            f"VNA가 응답하지 않습니다 (받은 값: {reply!r}). 포트와 장비 전원을 확인해 주세요."
        )


def parse_packet(chunk: bytes, points: int) -> tuple[int, complex]:
    """One FIFO packet as (point index, S11 = S11 channel / reference). S21 is dropped."""
    ref_re, ref_im, s11_re, s11_im, _, _, index = PACKET.unpack_from(chunk, 0)
    if index >= points:
        raise DeviceError(f"장비가 범위 밖의 점 번호 {index}를 보냈습니다 (점 {points}개).")
    reference = complex(ref_re, ref_im)
    if reference == 0:
        raise DeviceError(f"{index}번 점의 기준 신호가 0입니다. 다시 측정해 주세요.")
    return index, complex(s11_re, s11_im) / reference


def collect(port: SerialPort, points: int, clock: Clock) -> list[complex]:
    """Read FIFO packets until every index 0..points-1 is filled, within COLLECT_S."""
    deadline = clock.now() + COLLECT_S
    values: dict[int, complex] = {}
    while len(values) < points:
        if clock.now() >= deadline:
            raise DeviceError(
                f"{COLLECT_S:g}초 안에 {points}점을 다 받지 못했습니다 ({len(values)}점). "
                "점 개수를 줄이거나 다시 측정해 주세요."
            )
        count = min(MAX_BATCH, points - len(values))
        port.write(bytes((0x18, 0x30, count)))
        data = read_until(port, count * PACKET_BYTES, clock, deadline)
        for offset in range(0, len(data) - PACKET_BYTES + 1, PACKET_BYTES):
            index, gamma = parse_packet(data[offset : offset + PACKET_BYTES], points)
            values[index] = gamma
    return [values[i] for i in range(points)]


def to_sweep(frequencies_hz: tuple[int, ...], gammas: list[complex]) -> Sweep:
    """A zero reflection becomes -inf dB, which the sweep check rejects."""
    s11_db = [20 * math.log10(abs(g)) if g else -math.inf for g in gammas]
    return Sweep(
        f_mhz=tuple(hz / HZ_PER_MHZ for hz in frequencies_hz),
        s11_db=tuple(s11_db),
        gamma=tuple(gammas),
    )


class Saa2Source:
    """A SweepSource that measures once on a SAA-2. The port is closed on every path."""

    source = "usb"

    def __init__(
        self,
        port: str,
        sweep_range: SweepRange,
        opener: Opener = open_serial,
        clock: Clock | None = None,
    ) -> None:
        self.port = port
        self.sweep_range = sweep_range
        self.opener = opener
        self.clock = clock or SystemClock()

    def read(self) -> Sweep:
        port = self.opener(self.port)
        try:
            gammas = self._measure(port)
        except OSError as error:  # pyserial errors, write timeouts included
            raise DeviceError(f"USB 통신 중 오류가 났습니다. 케이블을 확인해 주세요. ({error})")
        finally:
            port.close()
        return to_sweep(axis_hz(self.sweep_range), gammas)

    def _measure(self, port: SerialPort) -> list[complex]:
        identify(port, self.clock)
        for command in range_commands(self.sweep_range):
            port.write(command)
        self.clock.sleep(SETTLE_S)
        port.write(CLEAR_FIFO)
        return collect(port, self.sweep_range.points, self.clock)
