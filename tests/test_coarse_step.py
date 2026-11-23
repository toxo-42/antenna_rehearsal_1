"""Too few measured points across a resonance: the card says so and gives a narrower range."""

from dataclasses import asdict

from src.models import AntennaKind, CalMode, Card, Sweep
from src.verdict import build_card
from tests.diag_helpers import antenna, magnitude_sweep

# A matched band from 595 to 605 MHz around a 600 MHz resonance.
BAND_10 = {590.0: 0.0, 595.0: -10.0, 600.0: -20.0, 605.0: -10.0, 610.0: 0.0}
SHALLOW = [0, 0, -8, 0, 0]


def card(sweep: Sweep, target: float, kind: AntennaKind = AntennaKind.MONOPOLE) -> Card:
    return build_card(sweep, antenna(target, kind), CalMode.VNA)


def coarse_card() -> Card:
    """500~700 MHz in 5 MHz steps: the 10 MHz band holds only 2 of them."""
    values = [BAND_10.get(500.0 + 5.0 * i, 0.0) for i in range(41)]
    return card(magnitude_sweep(values, start=500.0, step=5.0), 600.0)


def test_five_steps_across_the_band_are_enough() -> None:
    values = [0.0] * 101  # 500~700 MHz in 2 MHz steps
    dips = {47: -10.0, 48: -15.0, 49: -18.0, 50: -20.0, 51: -18.0, 52: -15.0, 53: -10.0}
    for index, db in dips.items():  # band 594~606 MHz: 12 MHz over 2 MHz steps is 6
        values[index] = db

    assert card(magnitude_sweep(values, start=500.0, step=2.0), 600.0).remeasure is None


def test_a_band_with_under_five_steps_asks_for_a_narrower_range() -> None:
    again = coarse_card().remeasure

    assert again is not None
    assert (again.start_mhz, again.stop_mhz) == (480, 720)
    assert "간격 5.00 MHz" in again.note and "10.00 MHz" in again.note
    assert "480~720 MHz 범위로 좁혀서 다시 측정" in again.note


def test_the_diagnoses_stay_as_they_were() -> None:
    assert [d.key for d in coarse_card().diagnoses] == ["narrow"]


def test_a_shallow_resonance_is_judged_by_the_typical_bandwidth() -> None:
    # 420 MHz, no band: a monopole's usual 8 % is 33.6 MHz. 10 MHz steps give 3.36, 6 MHz give 5.6.
    coarse = card(magnitude_sweep(SHALLOW, start=400.0, step=10.0), 420.0).remeasure
    fine_values = [0, 0, 0, 0, 0, -8, 0, 0, 0]
    fine = card(magnitude_sweep(fine_values, start=390.0, step=6.0), 420.0).remeasure

    assert coarse is not None and (coarse.start_mhz, coarse.stop_mhz) == (336, 504)
    assert fine is None


def test_exactly_five_steps_is_enough() -> None:
    # 400 MHz, no band, patch: the usual 2.5 % is 10 MHz, and 2 MHz steps make exactly 5.
    values = [0.0] * 11
    values[5] = -8.0
    patch = AntennaKind.PATCH

    assert card(magnitude_sweep(values, start=390.0, step=2.0), 400.0, patch).remeasure is None
    wider = card(magnitude_sweep(values, start=389.5, step=2.1), 400.0, patch).remeasure
    assert wider is not None


def test_no_selected_resonance_gives_no_range() -> None:
    assert card(magnitude_sweep(SHALLOW, start=400.0, step=10.0), 900.0).remeasure is None


def test_an_invalid_sweep_gives_no_range() -> None:
    sweep = magnitude_sweep([0.3, 0, -8, 0, 0], start=400.0, step=10.0)

    assert card(sweep, 420.0).remeasure is None


def test_the_note_never_reads_as_a_length_direction() -> None:
    again = coarse_card().remeasure

    assert again is not None
    assert not any(word in again.note for word in ("늘리", "줄이", "자르", "덧붙"))


def test_serialized_card_always_has_the_remeasure_key() -> None:
    with_range = asdict(coarse_card())
    without = asdict(card(magnitude_sweep(SHALLOW, start=400.0, step=10.0), 900.0))

    assert list(with_range) == ["stage", "headline", "status", "diagnoses", "remeasure"]
    assert list(with_range["remeasure"]) == ["start_mhz", "stop_mhz", "note"]
    assert list(without) == list(with_range) and without["remeasure"] is None
