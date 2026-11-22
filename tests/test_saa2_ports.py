"""Which serial port is offered first. No hardware needed."""

from dataclasses import dataclass

from src import saa2


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
