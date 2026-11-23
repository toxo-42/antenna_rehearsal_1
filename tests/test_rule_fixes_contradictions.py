"""One card never gives two opposite instructions: a third mode or a weak fundamental removes
the length rules, and an invalid sweep keeps its own headline."""

from pathlib import Path

import pytest

from src.models import Antenna, AntennaKind, CalMode, Card, CardStage, Sweep
from src.sweep_parser import parse_sweep_csv
from src.verdict import HEADLINES, LENGTH_FIRST_HEADLINE, build_card
from tests.diag_helpers import antenna, dip_sweep, gamma_sweep, keys, magnitude_sweep

DATA = Path(__file__).resolve().parent / "data"
LENGTH_KEYS = {"too_short", "too_long", "feed_lead", "reactance"}


def load(name: str) -> Sweep:
    return parse_sweep_csv((DATA / name).read_text(encoding="utf-8"))


def measured_card(name: str, target: float) -> Card:
    return build_card(load(name), antenna(target), CalMode.VNA)


def card_keys(card: Card) -> list[str]:
    return [d.key for d in card.diagnoses]


def test_third_mode_removes_the_length_rules_on_a_measured_file() -> None:
    card = measured_card("monopole_12cm.csv", 1750.0)

    assert "third_mode" in card_keys(card)
    assert not LENGTH_KEYS & set(card_keys(card))
    assert card.headline == HEADLINES[card.stage]


def test_third_mode_removes_the_length_first_headline() -> None:
    # 600 MHz is shallow and 7 % above the 560 MHz target: length first without the third mode.
    sweep = dip_sweep({200.0: -20.0, 600.0: -8.0}, start=100.0, stop=800.0)

    card = build_card(sweep, antenna(560.0), CalMode.VNA)

    assert card_keys(card) == ["match_unknown", "common_mode", "third_mode"]
    assert card.stage is CardStage.UNMATCHED
    assert card.headline == HEADLINES[CardStage.UNMATCHED]


@pytest.mark.parametrize("target", [2000.0, 2300.0])
def test_weak_fundamental_removes_the_length_rules_on_a_measured_file(target: float) -> None:
    card = measured_card("monopole_10cm_weak.csv", target)

    assert "weak_fundamental" in card_keys(card)
    assert not LENGTH_KEYS & set(card_keys(card))
    assert card.headline == HEADLINES[card.stage]
    assert card.headline != LENGTH_FIRST_HEADLINE


def test_third_mode_removes_reactance() -> None:
    # R 50 ohm with X left over at a shallow resonance gives `reactance` on its own.
    freqs = [100.0 + 10.0 * i for i in range(71)]
    gamma = [complex(0.999, 0.0)] * len(freqs)
    gamma[freqs.index(200.0)] = complex(0.05, 0.0)
    gamma[freqs.index(600.0)] = (complex(50, 40) - 50) / (complex(50, 40) + 50)
    with_base = gamma_sweep(freqs, gamma)
    gamma[freqs.index(200.0)] = complex(0.999, 0.0)
    alone = gamma_sweep(freqs, gamma)

    assert "reactance" in keys(alone, antenna(600.0))
    found = keys(with_base, antenna(600.0))
    assert "third_mode" in found and "reactance" not in found


def test_an_invalid_sweep_keeps_the_invalid_headline() -> None:
    sweep = magnitude_sweep([0.3, 0, -8, 0, 0], start=400.0, step=10.0)

    card = build_card(sweep, antenna(400.0), CalMode.VNA)

    assert card.stage is CardStage.INVALID
    assert card.headline == HEADLINES[CardStage.INVALID]
    assert card_keys(card) == ["positive_s11"]


def with_length(target: float, length_cm: float) -> Antenna:
    return Antenna(name="t", kind=AntennaKind.MONOPOLE, target_mhz=target, length_cm=length_cm)


def test_a_resonance_at_the_expected_frequency_is_not_a_third_mode() -> None:
    sweep = dip_sweep({210.0: -8.0, 620.0: -8.0}, start=100.0, stop=800.0)

    assert "third_mode" in keys(sweep, antenna(625.0))
    assert "third_mode" not in keys(sweep, with_length(625.0, 12.0))


def test_the_fifth_mode_of_the_weak_expected_dip_is_not_a_cable_resonance() -> None:
    dips = {200.0: -4.0, 450.0: -20.0, 1000.0: -20.0}
    sweep = dip_sweep(dips, start=100.0, stop=1200.0)

    found = keys(sweep, with_length(200.0, 37.5))

    assert found == ["weak_fundamental"]


def test_a_resonance_off_the_mode_ratios_is_still_reported_with_a_weak_expected_dip() -> None:
    dips = {200.0: -4.0, 450.0: -20.0, 800.0: -20.0}
    sweep = dip_sweep(dips, start=100.0, stop=1200.0)

    assert keys(sweep, with_length(200.0, 37.5)) == ["weak_fundamental", "other_resonance"]
