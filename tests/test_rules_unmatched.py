"""Rules for the `unmatched` stage: resistance, reactance direction, and missing complex data."""

import pytest

from src.models import Stage, Sweep
from src.synthetic import rlc
from tests.diag_helpers import (
    antenna,
    context,
    find,
    gamma_sweep,
    impedance_sweep,
    keys,
    magnitude_sweep,
)

FREQS = (400.0, 430.0, 460.0)
SHORTEN_CAUTION = "초기 추정. 한 번에 절반씩, 자르기 전에 다시 측정"
LENGTHEN_CAUTION = "초기 추정. 한 번에 절반씩, 자르지 말고 덧붙여서 확인"
RETEST = "더 촘촘한 간격으로 재측정"


def dip_with(impedance: complex, low_side: complex = 5 - 200j) -> Sweep:
    """An unmatched resonance at 430 MHz with the given impedance; almost full reflection around."""
    return impedance_sweep(FREQS, [low_side, impedance, 5 + 200j])


@pytest.mark.parametrize(
    ("r_ohm", "key"),
    [(29.99, "r_low"), (30.0, "reactance"), (90.0, "reactance"), (90.01, "r_high")],
)
def test_resistance_at_the_resonance_picks_the_rule(r_ohm: float, key: str) -> None:
    sweep = dip_with(complex(r_ohm, 30.0))
    ant = antenna(430.0)
    assert context(sweep, ant).classification.stage is Stage.UNMATCHED

    assert keys(sweep, ant) == [key, "common_mode"]


def test_reactance_direction_comes_from_the_target_not_the_dip() -> None:
    sweep = gamma_sweep(FREQS, [rlc(425.0, 50.0, 36.0)(f) for f in FREQS])
    ant = antenna(420.0)  # X is +42 ohm at the 430 MHz dip but negative at 420 MHz

    assert keys(sweep, ant) == ["reactance", "common_mode"]
    action = find(sweep, ant, "reactance").action
    assert "늘리는" in action and "줄이는" not in action
    assert LENGTHEN_CAUTION in action
    assert "자르기 전에" not in action


def test_reactance_says_shorten_when_x_at_the_target_is_positive() -> None:
    sweep = gamma_sweep(FREQS, [rlc(425.0, 50.0, 36.0)(f) for f in FREQS])

    action = find(sweep, antenna(440.0), "reactance").action

    assert "줄이는" in action and "늘리는" not in action
    assert SHORTEN_CAUTION in action


def test_reactance_gives_no_direction_when_x_at_the_target_is_zero() -> None:
    sweep = dip_with(50 + 40j, low_side=5 - 40j)  # X = -40 at 400 MHz, +40 at 430 MHz
    ant = antenna(415.0)
    assert keys(sweep, ant) == ["reactance", "common_mode"]

    action = find(sweep, ant, "reactance").action

    assert RETEST in action
    assert "줄이는" not in action and "늘리는" not in action


def test_reactance_gives_no_direction_when_the_target_is_outside_the_sweep() -> None:
    sweep = dip_with(50 + 40j)

    action = find(sweep, antenna(470.0), "reactance").action

    assert RETEST in action
    assert "줄이는" not in action and "늘리는" not in action


def test_reactance_gives_no_direction_when_x_at_the_target_is_not_finite() -> None:
    dip, high_side = (50 + 40j - 50) / (50 + 40j + 50), (5 + 200j - 50) / (5 + 200j + 50)
    sweep = gamma_sweep(FREQS, [1 + 1e-310j, dip, high_side])  # 400 MHz is almost an open
    ant = antenna(415.0)
    assert keys(sweep, ant) == ["reactance", "common_mode"]

    action = find(sweep, ant, "reactance").action

    assert RETEST in action
    assert "줄이는" not in action and "늘리는" not in action


def test_match_unknown_without_complex_data() -> None:
    sweep = magnitude_sweep([0, 0, -2, -8, -2, 0, 0])
    ant = antenna(430.0)
    assert context(sweep, ant).classification.stage is Stage.UNMATCHED

    assert keys(sweep, ant) == ["match_unknown", "common_mode"]


def test_r_low_for_a_monopole_names_the_quarter_wave_size() -> None:
    sweep = dip_with(20 + 10j)  # -6.99 dB: a resonance at 430 MHz, but unmatched
    assert keys(sweep, antenna(420.0)) == ["r_low", "common_mode"]

    action = find(sweep, antenna(420.0), "r_low").action

    assert "17.9 cm" in action  # 7500 / 420: from the target, not the 430 MHz resonance
    assert "라디알" in action
