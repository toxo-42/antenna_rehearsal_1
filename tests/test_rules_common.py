"""Rules that apply across stages: third mode, other resonances, and uncalibrated."""

import pytest

from src.models import AntennaKind, CalMode, Stage, Sweep
from tests.diag_helpers import antenna, context, dip_sweep, find, keys

CAUTION = ("초기 추정", "한 번에 절반씩", "자르기 전에 다시 측정")


def two_dips(upper_mhz: float, lower_db: float = -20.0, lower_mhz: float = 200.0) -> Sweep:
    """A matched resonance at `upper_mhz` plus a lower one; the target is the upper resonance."""
    return dip_sweep({lower_mhz: lower_db, upper_mhz: -20.0}, start=100.0, stop=800.0)


@pytest.mark.parametrize(
    ("upper_mhz", "key"),
    [
        (520.0, "third_mode"),  # 2.6
        (680.0, "third_mode"),  # 3.4
        (510.0, "other_resonance"),  # 2.55
        (690.0, "other_resonance"),  # 3.45
    ],
)
def test_third_mode_ratio_limits_are_inclusive(upper_mhz: float, key: str) -> None:
    sweep = two_dips(upper_mhz)
    ant = antenna(upper_mhz)
    assert context(sweep, ant).classification.stage is Stage.NARROW

    assert keys(sweep, ant) == [key, "narrow"]
    assert "200.00" in find(sweep, ant, key).evidence


def test_third_mode_action_keeps_the_length_caution() -> None:
    action = find(two_dips(600.0), antenna(600.0), "third_mode").action

    assert "1/3" in action
    assert "확신 없이 자르지 말 것" in action
    assert all(part in action for part in CAUTION)


def test_third_mode_applies_in_any_stage_with_a_selected_resonance() -> None:
    ant = antenna(610.0)  # outside the 595..605 MHz band
    assert context(two_dips(600.0), ant).classification.stage is Stage.OFFTARGET

    assert keys(two_dips(600.0), ant) == ["too_long", "feed_lead", "third_mode"]


def test_third_mode_leaves_out_other_resonance_even_with_more_resonances() -> None:
    sweep = dip_sweep({200.0: -20.0, 400.0: -20.0, 600.0: -20.0}, start=100.0, stop=800.0)

    assert keys(sweep, antenna(600.0)) == ["third_mode", "narrow"]


def test_third_mode_is_for_monopoles_only() -> None:
    ant = antenna(600.0, AntennaKind.PATCH)

    assert keys(two_dips(600.0), ant) == ["other_resonance", "narrow"]


def test_a_higher_resonance_is_not_a_third_mode_base() -> None:
    sweep = dip_sweep({200.0: -20.0, 600.0: -20.0}, start=100.0, stop=800.0)
    ant = antenna(200.0)  # the other resonance is 3x higher, not lower

    assert "third_mode" not in keys(sweep, ant)


def test_third_mode_evidence_names_the_first_matching_resonance() -> None:
    sweep = dip_sweep({180.0: -20.0, 200.0: -20.0, 600.0: -20.0}, start=100.0, stop=800.0)

    evidence = find(sweep, antenna(600.0), "third_mode").evidence

    assert "200.00" in evidence and "180.00" not in evidence


def test_other_resonance_evidence_names_the_one_nearest_the_target() -> None:
    sweep = dip_sweep({200.0: -20.0, 300.0: -20.0, 600.0: -20.0}, start=100.0, stop=800.0)

    evidence = find(sweep, antenna(600.0, AntennaKind.PATCH), "other_resonance").evidence

    assert "300.00" in evidence and "200.00" not in evidence


def test_other_resonance_skips_the_one_used_by_length_far() -> None:
    sweep = dip_sweep({200.0: -20.0}, start=100.0, stop=800.0)

    assert keys(sweep, antenna(600.0)) == ["length_far"]


def test_other_resonance_after_length_far_takes_the_next_matched_one() -> None:
    sweep = dip_sweep({150.0: -20.0, 200.0: -8.0, 300.0: -20.0}, start=100.0, stop=800.0)
    ant = antenna(600.0)

    assert keys(sweep, ant) == ["length_far", "other_resonance"]
    assert "300.00" in find(sweep, ant, "length_far").evidence
    assert "150.00" in find(sweep, ant, "other_resonance").evidence  # 200 MHz is unmatched


def test_uncalibrated_only_for_unknown_calibration() -> None:
    sweep = two_dips(600.0, lower_db=-8.0, lower_mhz=300.0)  # 2x: not a third-mode base

    assert keys(sweep, antenna(600.0), CalMode.VNA) == ["narrow"]
    assert keys(sweep, antenna(600.0), CalMode.UNKNOWN) == ["narrow", "uncalibrated"]
