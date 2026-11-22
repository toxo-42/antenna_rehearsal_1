"""Rules for the `offtarget` stage: length direction, the feed lead, and the band-edge case."""

from src.models import Antenna, AntennaKind, Stage, Sweep
from tests.diag_helpers import antenna, context, find, keys, magnitude_sweep

# Resonance at 420 MHz, band 405..435 MHz, spacing 10 MHz.
ONE_DIP = magnitude_sweep([0, 0, -5, -15, -30, -15, -5, 0, 0, 0, 0], start=380.0)
CAUTION = ("초기 추정", "한 번에 절반씩", "자르기 전에 다시 측정")


def patch(target: float) -> Antenna:
    return antenna(target, AntennaKind.PATCH)


def test_resonance_below_a_target_outside_the_band_is_too_long() -> None:
    assert keys(ONE_DIP, patch(437.0)) == ["too_long", "feed_lead"]

    action = find(ONE_DIP, patch(437.0), "too_long").action
    assert "약 4 %" in action and "줄이는" in action  # (420 - 437) / 437 = -3.89 %
    assert "패치 길이(공진 방향 변)" in action
    assert all(part in action for part in CAUTION)


def test_resonance_above_a_target_outside_the_band_is_too_short() -> None:
    assert keys(ONE_DIP, patch(403.0)) == ["too_short"]

    action = find(ONE_DIP, patch(403.0), "too_short").action
    assert "약 4 %" in action and "늘리는" in action  # (420 - 403) / 403 = +4.22 %
    assert all(part in action for part in CAUTION)


def test_target_inside_the_band_but_near_its_edge_is_band_edge_only() -> None:
    ant = patch(433.0)  # 2 MHz inside the 435 MHz edge
    assert context(ONE_DIP, ant).classification.stage is Stage.OFFTARGET

    assert keys(ONE_DIP, ant) == ["band_edge"]
    action = find(ONE_DIP, ant, "band_edge").action
    assert "촘촘한 간격" in action
    assert "줄이는" not in action and "늘리는" not in action


def test_band_edge_when_the_resonance_sits_exactly_on_the_target() -> None:
    # Resonance 420 MHz, band 418.33..450.2 MHz: the low edge is 1.67 MHz from the dip itself.
    sweep = magnitude_sweep([0, -5, -11, -10.5, -10.5, -10.2, 0], start=400.0)
    ant = patch(420.0)
    result = context(sweep, ant).classification
    assert result.stage is Stage.OFFTARGET and result.offset_pct == 0.0

    assert keys(sweep, ant) == ["band_edge"]


def test_offtarget_amount_rounds_an_exact_half_percent_up() -> None:
    sweep = Sweep(f_mhz=(31.8, 32.0, 32.2, 32.4, 32.6), s11_db=(0.0, -8.0, -18.0, -8.0, 0.0))
    ant = patch(40.0)  # (32.2 - 40) / 40 = -19.5 %

    assert keys(sweep, ant) == ["too_long", "feed_lead"]
    assert "약 20 %" in find(sweep, ant, "too_long").action


def test_amount_that_rounds_to_zero_reads_as_under_one_percent() -> None:
    freqs = tuple(399.6 + 0.2 * i for i in range(5))
    sweep = Sweep(f_mhz=freqs, s11_db=(0.0, -8.0, -18.0, -8.0, 0.0))  # band 399.84..400.16
    ant = patch(400.3)  # -0.07 %

    assert keys(sweep, ant) == ["too_long", "feed_lead"]
    action = find(sweep, ant, "too_long").action
    assert "1 % 미만" in action
    assert "0 %" not in action
