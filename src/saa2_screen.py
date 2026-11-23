"""SAA-2 screenshot as PNG. Only identify and the screenshot request are sent, so the device
screen keeps working. Taken after a USB measurement, it only shows "USB MODE".

The header is little endian like every other SAA-2 field, but the RGB565 pixels are big endian
(checked on a real measure screen, 2026-11-22: the yellow trace arrives as `ff e0`).
"""

import struct
import zlib

from src import saa2

SCREEN_REQUEST = b"\x20\xee\x00"
HEADER = struct.Struct("<HHB")  # width, height, bits per pixel
BITS = 16
MAX_SIDE = 1024
SCREEN_S = 10.0
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def capture_png(port_name: str, opener: saa2.Opener, clock: saa2.Clock | None = None) -> bytes:
    """Read the device screen and return it as a PNG. The port is closed on every path."""
    clock = clock or saa2.SystemClock()
    width, height, pixels = saa2.with_port(port_name, opener, lambda p: _read_screen(p, clock))
    return rgb565_png(width, height, pixels)


def _read_screen(port: saa2.SerialPort, clock: saa2.Clock) -> tuple[int, int, bytes]:
    saa2.identify(port, clock)
    port.write(SCREEN_REQUEST)
    deadline = clock.now() + SCREEN_S
    header = saa2.read_until(port, HEADER.size, clock, deadline)
    if len(header) < HEADER.size:
        raise saa2.DeviceError("장비가 화면 정보를 보내지 않았습니다. 다시 시도해 주세요.")
    width, height, bits = HEADER.unpack(header)
    if bits != BITS or not (0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE):
        raise saa2.DeviceError(f"알 수 없는 화면 형식입니다 ({width}×{height}, {bits}비트).")
    pixels = saa2.read_until(port, width * height * 2, clock, deadline)
    if len(pixels) < width * height * 2:
        raise saa2.DeviceError("화면을 끝까지 받지 못했습니다. 다시 시도해 주세요.")
    return width, height, pixels


def rgb565_png(width: int, height: int, pixels: bytes) -> bytes:
    """An 8-bit RGB PNG from big endian RGB565 pixels."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # filter: none
        for offset in range(y * width * 2, (y + 1) * width * 2, 2):
            value = pixels[offset] << 8 | pixels[offset + 1]
            red, green, blue = value >> 11, (value >> 5) & 0x3F, value & 0x1F
            rows += bytes((red * 255 // 31, green * 255 // 63, blue * 255 // 31))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunks = [_chunk(b"IHDR", ihdr), _chunk(b"IDAT", zlib.compress(bytes(rows))), _chunk(b"IEND")]
    return PNG_SIGNATURE + b"".join(chunks)


def _chunk(kind: bytes, data: bytes = b"") -> bytes:
    crc = zlib.crc32(kind + data)
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)
