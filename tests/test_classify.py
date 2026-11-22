import pytest

from src.classify import classify
from src.models import Antenna, AntennaKind, Stage, Sweep


def antenna(target: float, kind: AntennaKind = AntennaKind.PATCH) -> Antenna:
    return Antenna(name="t", kind=kind, target_mhz=target)


def make_sweep(values: list[float], start: float) -> Sweep:
    freqs = tuple(start + 10.0 * i for i in range(len(values)))
    return Sweep(f_mhz=freqs, s11_db=tuple(values))


# Resonance at 420 MHz, band 405..435 MHz (7.14 %), spacing 10 MHz.
ONE_DIP = make_sweep([0, 0, -5, -15, -30, -15, -5, 0, 0, 0, 0], start=380.0)


def test_good_when_target_is_well_inside_the_band() -> None:
    result = classify(ONE_DIP, antenna(428.0))

    assert result.stage is Stage.GOOD
    assert result.selected is not None and result.selected.f_mhz == 420.0
    assert result.offset_pct == pytest.approx((420.0 - 428.0) / 428.0 * 100)
    assert result.others == ()


def test_offtarget_when_target_is_outside_the_band() -> None:
    assert classify(ONE_DIP, antenna(437.0)).stage is Stage.OFFTARGET


def test_offtarget_when_target_is_within_half_a_step_of_the_band_edge() -> None:
    assert classify(ONE_DIP, antenna(433.0)).stage is Stage.OFFTARGET  # 2 MHz from 435
    assert classify(ONE_DIP, antenna(407.0)).stage is Stage.OFFTARGET  # 2 MHz from 405
    assert classify(ONE_DIP, antenna(429.9)).stage is Stage.GOOD  # 5.1 MHz from 435


def test_narrow_is_checked_before_the_band_edge_rule() -> None:
    result = classify(ONE_DIP, antenna(433.0, AntennaKind.MONOPOLE))  # 7.14 % < 8 %

    assert result.stage is Stage.NARROW


def test_unmatched_when_resonance_is_shallower_than_match_threshold() -> None:
    sweep = make_sweep([0, 0, -2, -8, -2, 0, 0], start=400.0)

    result = classify(sweep, antenna(430.0))

    assert result.stage is Stage.UNMATCHED
    assert result.selected is not None and result.selected.band is None


def test_none_when_no_resonance_is_within_20_percent_of_target() -> None:
    result = classify(ONE_DIP, antenna(600.0))  # window 480..720

    assert result.stage is Stage.NONE
    assert result.selected is None
    assert result.offset_pct is None
    assert [r.f_mhz for r in result.others] == [420.0]


def test_window_edge_is_inclusive() -> None:
    assert classify(ONE_DIP, antenna(525.0)).stage is not Stage.NONE  # 420 = 525 * 0.8
    assert classify(ONE_DIP, antenna(350.0)).stage is not Stage.NONE  # 420 = 350 * 1.2


def test_candidate_whose_band_contains_target_beats_a_nearer_one() -> None:
    # 400 MHz: band up to 432 MHz. 450 MHz: nearer to 431 MHz but unmatched (-7 dB).
    sweep = make_sweep([0, -5, -15, -30, -20, -15, -12, -2, -7, -1, 0], start=370.0)

    result = classify(sweep, antenna(431.0))

    assert result.selected is not None and result.selected.f_mhz == 400.0
    assert [r.f_mhz for r in result.others] == [450.0]


def test_nearest_candidate_wins_when_no_band_contains_target() -> None:
    sweep = make_sweep([0, -5, -15, -30, -20, -15, -12, -2, -7, -1, 0], start=370.0)

    result = classify(sweep, antenna(445.0))

    assert result.selected is not None and result.selected.f_mhz == 450.0
    assert result.stage is Stage.UNMATCHED
    assert [r.f_mhz for r in result.others] == [400.0]


def test_others_are_sorted_by_distance_from_target() -> None:
    values = [0, -20, 0, 0, 0, 0, 0, 0, 0, -20, 0, 0, -20, 0]
    sweep = make_sweep(values, start=100.0)  # resonances at 110, 190, 220 MHz

    result = classify(sweep, antenna(400.0))

    assert result.stage is Stage.NONE
    assert [r.f_mhz for r in result.others] == [220.0, 190.0, 110.0]


def test_offtarget_is_checked_before_narrow() -> None:
    result = classify(ONE_DIP, antenna(437.0, AntennaKind.MONOPOLE))  # outside band, 7.14 %

    assert result.stage is Stage.OFFTARGET


def test_resonance_just_beyond_20_percent_is_not_a_candidate() -> None:
    assert classify(ONE_DIP, antenna(349.0)).stage is Stage.NONE  # 420 > 349 * 1.2
    assert classify(ONE_DIP, antenna(526.0)).stage is Stage.NONE  # 420 < 526 * 0.8


@pytest.mark.parametrize("resonance_mhz", [346.4, 519.6])
def test_window_edge_is_inclusive_despite_rounding(resonance_mhz: float) -> None:
    freqs = (resonance_mhz - 10.0, resonance_mhz, resonance_mhz + 10.0)
    sweep = Sweep(f_mhz=freqs, s11_db=(0.0, -20.0, 0.0))
    assert abs(resonance_mhz - 433.0) > 433.0 * 20 / 100  # rounding puts it outside

    assert classify(sweep, antenna(433.0)).stage is not Stage.NONE


def test_band_edge_margin_between_quarter_and_half_step_is_offtarget() -> None:
    assert classify(ONE_DIP, antenna(431.5)).stage is Stage.OFFTARGET  # 3.5 MHz from 435


def test_bandwidth_exactly_at_typical_value_is_not_narrow() -> None:
    freqs = (405.68, 415.68, 433.0, 450.32, 460.32)
    sweep = Sweep(f_mhz=freqs, s11_db=(0.0, -10.0, -30.0, -10.0, 0.0))
    assert (450.32 - 415.68) / 433.0 * 100 < 8.0  # rounding puts it under 8 %

    assert classify(sweep, antenna(433.0, AntennaKind.MONOPOLE)).stage is Stage.GOOD


def test_target_on_an_interpolated_band_edge_counts_as_inside() -> None:
    freqs = tuple(399.6 + 0.2 * i for i in range(5))
    sweep = Sweep(f_mhz=freqs, s11_db=(0.0, -8.0, -18.0, -8.0, 0.0))  # band 399.84..400.16

    assert classify(sweep, antenna(399.84)).stage is Stage.NARROW  # not offtarget


def test_target_exactly_half_a_step_from_the_edge_is_not_near_it() -> None:
    freqs = (406.9, 410.0, 413.1, 416.2, 419.3, 422.4, 425.5, 428.6, 431.7)
    values = (0.0, 0.0, -10.0, -20.0, -30.0, -20.0, -10.0, 0.0, 0.0)  # band 413.1..425.5
    assert 414.65 - 413.1 < 3.1 / 2  # rounding puts it under half a step

    assert classify(Sweep(f_mhz=freqs, s11_db=values), antenna(414.65)).stage is Stage.GOOD


def test_band_edge_rule_uses_the_spacing_at_the_edge_not_the_sweep_average() -> None:
    freqs = (400.0, 410.0, 420.0, 430.0, 440.0, 450.0, 460.0, 470.0, 480.0, 1000.0)
    values = (0.0, -5.0, -15.0, -30.0, -15.0, -5.0, 0.0, 0.0, 0.0, 0.0)  # band 415..445
    sweep = Sweep(f_mhz=freqs, s11_db=values)

    assert classify(sweep, antenna(432.0)).stage is Stage.GOOD  # 13 MHz inside the edge
    assert classify(sweep, antenna(442.0)).stage is Stage.OFFTARGET  # 3 MHz, local step 10
