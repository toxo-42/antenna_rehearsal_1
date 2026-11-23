"""The SAA-2 screen for the HTTP route, with the same Korean errors as a USB measurement."""

import threading

from src import saa2, saa2_screen
from src.service import BusyError, DeviceError, InputError


def device_screen(port: str | None, opener: saa2.Opener, lock: threading.Lock) -> bytes:
    """The SAA-2 screen as PNG. Not while a USB measurement holds the port (BusyError)."""
    if port is None or not port.strip():
        raise InputError("USB 포트(port)를 골라 주세요.")
    if not lock.acquire(blocking=False):
        raise BusyError("USB 측정이 진행 중입니다. 끝난 뒤 다시 시도해 주세요.")
    try:
        return saa2_screen.capture_png(port, opener)
    except saa2.DeviceError as error:
        raise DeviceError(str(error)) from None
    finally:
        lock.release()
