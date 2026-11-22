"""Rules for the `none` stage: feed faults, lossy, far resonance, out of range, and the fallback."""

import math

import pytest

from src.models import AntennaKind, Stage
from tests.diag_helpers import (
    antenna,
    context,
    dip_sweep,
    find,
    gamma_sweep,
    keys,
    magnitude_sweep,
)

FREQS = tuple(400.0 + 10.0 * i for i in range(11))
FLAT_MAGNITUDE = 0.95  # -0.45 dB: above the -1 dB line at every point


def flat_gamma(real: float) -> list[complex]:
    """The same reflection coefficient at every point, with an exact real part."""
    imag = math.sqrt(FLAT_MAGNITUDE**2 - real**2)
    return [complex(real, imag)] * len(FREQS)


def test_feed_fault_when_flat_without_complex_data() -> None:
    sweep = magnitude_sweep([-0.2] * 11)

    assert keys(sweep, antenna(450.0)) == ["feed_fault"]


@pytest.mark.parametrize(
    ("real", "key"),
    [
        (0.2, "feed_fault"),
        (0.5, "feed_fault"),
        (-0.5, "feed_fault"),
        (0.501, "feed_open"),
        (-0.501, "feed_short"),
    ],
)
def test_low_frequency_reflection_splits_the_feed_faults(real: float, key: str) -> None:
    sweep = gamma_sweep(FREQS, flat_gamma(real))

    assert keys(sweep, antenna(450.0)) == [key]


def test_feed_needs_90_percent_of_points_above_minus_1_db() -> None:
    nine_of_ten = magnitude_sweep([-0.5] * 9 + [-1.5])
    eight_of_ten = magnitude_sweep([-0.5] * 8 + [-1.5, -1.5])

    assert keys(nine_of_ten, antenna(450.0)) == ["feed_fault"]
    assert keys(eight_of_ten, antenna(450.0)) == ["no_resonance"]


def test_a_point_exactly_at_minus_1_db_is_not_above_it() -> None:
    sweep = magnitude_sweep([-0.5] * 8 + [-1.0, -1.0])

    assert keys(sweep, antenna(450.0)) == ["no_resonance"]


def test_points_just_above_minus_1_db_count_for_the_feed_shape() -> None:
    sweep = magnitude_sweep([-0.99] * 11)

    assert keys(sweep, antenna(450.0)) == ["feed_fault"]


def test_magnitude_only_sweep_outside_the_feed_shape_is_not_a_feed_fault() -> None:
    sweep = magnitude_sweep([-2.0] * 11)

    assert keys(sweep, antenna(450.0)) == ["no_resonance"]


def test_another_resonance_rules_out_feed_faults() -> None:
    sweep = dip_sweep({200.0: -20.0}, start=100.0, stop=700.0)  # 60 of 61 points at 0 dB
    ant = antenna(600.0)
    assert context(sweep, ant).classification.stage is Stage.NONE

    assert keys(sweep, ant) == ["length_far"]
    action = find(sweep, ant, "length_far").action
    assert "67 %" in action and "줄이는" in action


def test_length_far_rounds_an_exact_half_percent_up() -> None:
    sweep = dip_sweep({251.0: -20.0}, start=100.0, stop=300.0, step=1.0)

    action = find(sweep, antenna(200.0), "length_far").action  # 251 / 200 = +25.5 %

    assert "약 26 %" in action and "늘리는" in action


def test_lossy_title_does_not_claim_the_cause() -> None:
    sweep = magnitude_sweep([-3.0, -4.0, -5.0, -6.0, -7.0])

    assert "수 있음" in find(sweep, antenna(420.0), "lossy").title


def test_lossy_needs_30_percent_of_points_between_minus_10_and_minus_3_db() -> None:
    three_of_ten = magnitude_sweep([-2.0] * 7 + [-5.0] * 3)
    two_of_ten = magnitude_sweep([-2.0] * 8 + [-5.0] * 2)

    assert keys(three_of_ten, antenna(450.0)) == ["lossy"]
    assert keys(two_of_ten, antenna(450.0)) == ["no_resonance"]


def test_lossy_range_includes_both_ends() -> None:
    sweep = magnitude_sweep([-2.0] * 7 + [-3.0, -10.0, -10.0])

    assert keys(sweep, antenna(450.0)) == ["lossy"]


@pytest.mark.parametrize("outside_db", [-2.99, -10.01])
def test_lossy_range_excludes_values_just_outside_it(outside_db: float) -> None:
    sweep = magnitude_sweep([-2.0] * 7 + [outside_db] * 3)

    assert keys(sweep, antenna(450.0)) == ["no_resonance"]


@pytest.mark.parametrize("values", [[-0.5, -1.0, -1.5, -2.0, -2.5], [-2.5, -2.0, -1.5, -1.0, -0.5]])
def test_out_of_range_when_an_end_point_is_the_lowest(values: list[float]) -> None:
    sweep = magnitude_sweep(values)

    assert keys(sweep, antenna(420.0)) == ["out_of_range"]


def test_flat_trace_is_not_out_of_range() -> None:
    sweep = magnitude_sweep([-2.0] * 5)

    assert keys(sweep, antenna(420.0)) == ["no_resonance"]


def test_end_point_tied_with_an_interior_point_is_not_out_of_range() -> None:
    sweep = magnitude_sweep([-2.5, -1.0, -2.5, -1.0, -1.0])

    assert keys(sweep, antenna(420.0)) == ["no_resonance"]


def test_lossy_hides_out_of_range() -> None:
    sweep = magnitude_sweep([-3.0, -4.0, -5.0, -6.0, -7.0])  # last point is the lowest

    assert keys(sweep, antenna(420.0)) == ["lossy"]


def test_feed_fault_hides_out_of_range() -> None:
    sweep = magnitude_sweep([-0.1, -0.2, -0.3, -0.4, -0.5])  # last point is the lowest

    assert keys(sweep, antenna(420.0)) == ["feed_fault"]


@pytest.mark.parametrize(("sign", "key"), [(-1.0, "feed_short"), (1.0, "feed_open")])
def test_feed_short_and_feed_open_hide_out_of_range(sign: float, key: str) -> None:
    magnitudes = [0.99 - 0.005 * i for i in range(11)]  # -0.09..-0.54 dB, last point is the lowest
    sweep = gamma_sweep(FREQS, [complex(sign * m, 0.0) for m in magnitudes])

    assert keys(sweep, antenna(450.0)) == [key]


def test_lossy_needs_no_other_resonance() -> None:
    sweep = magnitude_sweep([-5.0] * 6 + [-20.0] + [-5.0] * 4, start=100.0)  # resonance 160 MHz
    ant = antenna(300.0)
    assert context(sweep, ant).classification.stage is Stage.NONE

    assert keys(sweep, ant) == ["length_far"]


def test_out_of_range_only_applies_when_no_resonance_is_near_the_target() -> None:
    values = [0, 0, -5, -15, -30, -15, -5, 0, 0, 0, -35]  # resonance 420 MHz, lower end point
    sweep = magnitude_sweep(values, start=380.0)
    ant = antenna(428.0, AntennaKind.PATCH)
    assert context(sweep, ant).classification.stage is Stage.GOOD

    assert keys(sweep, ant) == ["good"]


def test_far_resonance_and_out_of_range_can_appear_together() -> None:
    values = [0.0, -20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -25.0]
    sweep = magnitude_sweep(values, start=100.0, step=50.0)  # resonance 150 MHz, end 600 MHz

    assert keys(sweep, antenna(400.0)) == ["length_far", "out_of_range"]
