"""The range suggested for measuring again: it holds the target, and halves round up."""

from src.models import Antenna, AntennaKind, CalMode, Remeasure
from src.verdict import build_card
from tests.diag_helpers import antenna, dip_sweep, magnitude_sweep

SHALLOW = [0, 0, -8, 0, 0]


def test_the_range_is_extended_up_to_a_target_above_it() -> None:
    sweep = dip_sweep({200.0: -8.0}, start=100.0, stop=400.0)
    ant = Antenna(name="t", kind=AntennaKind.MONOPOLE, target_mhz=300.0, length_cm=37.5)

    again = build_card(sweep, ant, CalMode.VNA).remeasure

    assert again is not None
    assert (again.start_mhz, again.stop_mhz) == (160, 300)
    assert "160~300 MHz 범위로" in again.note


def test_the_range_is_extended_down_to_a_target_below_it() -> None:
    sweep = dip_sweep({250.0: -8.0}, start=100.0, stop=400.0)
    ant = Antenna(name="t", kind=AntennaKind.MONOPOLE, target_mhz=150.5, length_cm=30.0)

    again = build_card(sweep, ant, CalMode.VNA).remeasure

    assert again is not None
    assert (again.start_mhz, again.stop_mhz) == (150, 300)
    assert "150~300 MHz 범위로" in again.note


def test_a_target_inside_the_range_leaves_it_at_twenty_percent() -> None:
    again = build_card(
        magnitude_sweep(SHALLOW, start=400.0, step=10.0), antenna(420.0), CalMode.VNA
    ).remeasure

    assert again is not None and (again.start_mhz, again.stop_mhz) == (336, 504)


def remeasure_at(resonance_mhz: float) -> Remeasure | None:
    sweep = magnitude_sweep(SHALLOW, start=resonance_mhz - 20.0, step=10.0)
    return build_card(sweep, antenna(resonance_mhz), CalMode.VNA).remeasure


def test_a_half_rounds_up_not_to_the_even_number() -> None:
    again = remeasure_at(503.125)  # 402.5 and 603.75

    assert again is not None
    assert (again.start_mhz, again.stop_mhz) == (403, 604)
    assert "403~604 MHz 범위로" in again.note
