"""A shallow resonance far from the target gets length advice first; matching checks come along."""

import pytest

from src.models import CalMode, CardStage, Stage
from src.synthetic import rlc
from src.verdict import HEADLINES, build_card
from tests.diag_helpers import antenna, context, find, gamma_sweep, keys, magnitude_sweep

SHALLOW = [0, 0, -8, 0, 0]  # 400~440 MHz in 10 MHz steps, an unmatched dip at 420 MHz
COARSE = [0, -8, 0]  # 400/430/460 MHz, an unmatched dip at 430 MHz
RLC_FREQS = (400.0, 430.0, 460.0)
MATCH_KEYS = ["match_unknown", "common_mode"]


def test_shallow_resonance_five_percent_above_the_target_is_too_short() -> None:
    sweep, ant = magnitude_sweep(SHALLOW), antenna(400.0)  # 420 is exactly +5 %
    assert context(sweep, ant).classification.stage is Stage.UNMATCHED

    assert keys(sweep, ant) == ["too_short", *MATCH_KEYS]
    action = find(sweep, ant, "too_short").action
    assert "약 5 % 늘리는" in action and "줄이는" not in action


def test_shallow_resonance_below_the_target_is_too_long_with_the_feed_lead() -> None:
    sweep, ant = magnitude_sweep(SHALLOW), antenna(440.0)  # 420 is -4.55 %: not yet

    assert keys(sweep, ant) == MATCH_KEYS

    sweep = magnitude_sweep(SHALLOW, start=380.0)  # dip at 400 MHz, -9.09 %
    assert keys(sweep, ant) == ["too_long", "feed_lead", *MATCH_KEYS]
    assert "약 9 % 줄이는" in find(sweep, ant, "too_long").action


def test_under_five_percent_keeps_the_matching_advice_only() -> None:
    sweep, ant = magnitude_sweep(SHALLOW), antenna(401.0)  # 420 is +4.74 %

    assert keys(sweep, ant) == MATCH_KEYS


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (409.0, MATCH_KEYS),  # +5.13 % but 21 MHz is inside one 30 MHz step
        (400.0, ["too_short", *MATCH_KEYS]),  # exactly one step away counts
    ],
)
def test_an_offset_inside_one_measurement_step_is_not_a_length_error(
    target: float, expected: list[str]
) -> None:
    sweep = magnitude_sweep(COARSE, step=30.0)

    assert keys(sweep, antenna(target)) == expected


def test_length_advice_replaces_the_reactance_direction() -> None:
    sweep = gamma_sweep(RLC_FREQS, [rlc(425.0, 50.0, 36.0)(f) for f in RLC_FREQS])

    assert keys(sweep, antenna(420.0)) == ["reactance", "common_mode"]  # -2.3 %: as before
    assert keys(sweep, antenna(400.0)) == ["too_short", "common_mode"]
    assert keys(sweep, antenna(460.0)) == ["too_long", "feed_lead", "common_mode"]


def test_a_far_target_outside_the_sweep_still_gets_the_length_direction() -> None:
    sweep = gamma_sweep(RLC_FREQS, [rlc(425.0, 50.0, 36.0)(f) for f in RLC_FREQS])

    assert keys(sweep, antenna(470.0)) == ["too_long", "feed_lead", "common_mode"]


def test_headline_says_both_the_miss_and_the_shallow_match() -> None:
    card = build_card(magnitude_sweep(SHALLOW), antenna(400.0), CalMode.VNA)

    assert card.stage is CardStage.UNMATCHED
    assert card.headline == "공진이 목표 주파수에서 벗어나 있고 정합도 얕습니다"
    near = build_card(magnitude_sweep(SHALLOW), antenna(401.0), CalMode.VNA)
    assert near.headline == HEADLINES[CardStage.UNMATCHED]
