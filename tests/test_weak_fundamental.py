"""A monopole whose base resonance is weak: the resonance at three times it must not be read as
the base, and the third-mode resonance of a healthy monopole is not a cable problem."""

import pytest

from src.models import AntennaKind, Stage, Sweep
from tests.diag_helpers import antenna, context, dip_sweep, find, keys

WEAK_DB = -4.0  # a dip of 4 dB: deeper than a ripple (2 dB), not a resonance (-6 dB)


def weak_and_third(third_mhz: float = 600.0, weak_mhz: float = 200.0) -> Sweep:
    """A weak dip plus a matched resonance about three times higher."""
    return dip_sweep({weak_mhz: WEAK_DB, third_mhz: -20.0}, start=100.0, stop=800.0)


def test_far_resonance_at_three_times_a_weak_dip_is_not_a_length_error() -> None:
    sweep, ant = weak_and_third(), antenna(200.0)
    assert context(sweep, ant).classification.stage is Stage.NONE

    assert keys(sweep, ant) == ["weak_fundamental"]
    found = find(sweep, ant, "weak_fundamental")
    assert "600.00" in found.evidence and "200.00" in found.evidence and "3.00배" in found.evidence
    assert "곧은지" in found.action and "급전부" in found.action
    assert "늘리는" not in found.action and "줄이는" not in found.action


@pytest.mark.parametrize(
    ("third_mhz", "expected"),
    [
        (520.0, ["weak_fundamental"]),  # 2.6
        (680.0, ["weak_fundamental"]),  # 3.4
        (510.0, ["length_far"]),  # 2.55
        (690.0, ["length_far"]),  # 3.45
    ],
)
def test_weak_fundamental_ratio_limits_are_inclusive(third_mhz: float, expected: list[str]) -> None:
    assert keys(weak_and_third(third_mhz), antenna(200.0)) == expected


def test_without_a_weak_dip_the_far_resonance_keeps_the_length_advice() -> None:
    sweep = dip_sweep({600.0: -20.0}, start=100.0, stop=800.0)

    assert keys(sweep, antenna(200.0)) == ["length_far"]


def test_a_ripple_is_not_a_weak_fundamental() -> None:
    sweep = dip_sweep({200.0: -1.9, 600.0: -20.0}, start=100.0, stop=800.0)

    assert keys(sweep, antenna(200.0)) == ["length_far"]


def test_weak_fundamental_is_for_monopoles_only() -> None:
    assert keys(weak_and_third(), antenna(200.0, AntennaKind.PATCH)) == ["length_far"]


def test_selected_resonance_at_three_times_a_weak_dip_is_flagged_too() -> None:
    assert keys(weak_and_third(), antenna(600.0)) == ["weak_fundamental", "narrow"]


def test_a_shallow_lower_resonance_is_a_third_mode_base() -> None:
    sweep = dip_sweep({200.0: -8.0, 600.0: -20.0}, start=100.0, stop=800.0)

    assert keys(sweep, antenna(600.0)) == ["third_mode", "narrow"]


def test_third_mode_resonance_of_the_selected_one_is_not_a_cable_problem() -> None:
    sweep = dip_sweep({200.0: -20.0, 600.0: -20.0}, start=100.0, stop=800.0)

    assert keys(sweep, antenna(200.0)) == ["narrow"]
    assert keys(sweep, antenna(200.0, AntennaKind.PATCH)) == ["other_resonance", "good"]


@pytest.mark.parametrize(
    ("fifth_mhz", "expected"),
    [
        (900.0, ["narrow"]),  # 4.5
        (1100.0, ["narrow"]),  # 5.5
        (880.0, ["other_resonance", "narrow"]),  # 4.4
        (1120.0, ["other_resonance", "narrow"]),  # 5.6
    ],
)
def test_fifth_mode_resonance_is_not_a_cable_problem_either(
    fifth_mhz: float, expected: list[str]
) -> None:
    sweep = dip_sweep({200.0: -20.0, fifth_mhz: -20.0}, start=100.0, stop=1200.0)

    assert keys(sweep, antenna(200.0)) == expected
    patch = antenna(200.0, AntennaKind.PATCH)
    assert "other_resonance" in keys(sweep, patch)


def test_a_resonance_outside_the_third_mode_ratio_is_still_another_resonance() -> None:
    sweep = dip_sweep({200.0: -20.0, 500.0: -20.0, 600.0: -20.0}, start=100.0, stop=800.0)

    assert keys(sweep, antenna(200.0)) == ["other_resonance", "narrow"]
    assert "500.00" in find(sweep, antenna(200.0), "other_resonance").evidence
