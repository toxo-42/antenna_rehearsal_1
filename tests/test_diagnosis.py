"""Diagnosis keys for the 18 synthetic samples, from the table in spec/p2_diagnosis.md.

Expected values come from the spec table. Do not edit them to make a test pass.
"""

import pytest

from src.diagnosis import RULES, diagnose
from src.guides import guide_for
from src.models import POSITIVE_S11_DB, CalMode, Diagnosis
from src.synthetic import SAMPLE_NAMES, make_sample
from tests.diag_helpers import antenna, context, keys, magnitude_sweep

EXPECTED: dict[str, list[str]] = {
    "good": ["good"],
    "offtarget_low": ["too_long", "feed_lead"],
    "offtarget_high": ["too_short"],
    "narrow": ["narrow"],
    "unmatched_low_r": ["r_low", "common_mode"],
    "unmatched_high_r": ["r_high", "common_mode"],
    "far_low": ["length_far"],
    "far_high": ["length_far"],
    "open": ["feed_open"],
    "short": ["feed_short"],
    "lossy": ["lossy"],
    "positive": ["positive_s11"],
    "two_res": ["length_far", "other_resonance"],
    "third_mode": ["r_low", "common_mode", "third_mode"],
    "patch_good": ["good"],
    "patch_narrow": ["narrow"],
    "patch_low_r": ["r_low", "common_mode"],
    "patch_high_r": ["r_high", "common_mode"],
}

RULE_ORDER = [
    "positive_s11",
    "feed_short",
    "feed_open",
    "feed_fault",
    "lossy",
    "length_far",
    "weak_fundamental",
    "out_of_range",
    "too_short",
    "too_long",
    "feed_lead",
    "band_edge",
    "r_low",
    "r_high",
    "reactance",
    "match_unknown",
    "common_mode",
    "third_mode",
    "other_resonance",
    "narrow",
    "good",
    "uncalibrated",
]

CAUTION = {
    "줄이는": "초기 추정. 한 번에 절반씩, 자르기 전에 다시 측정",
    "늘리는": "초기 추정. 한 번에 절반씩, 자르지 말고 덧붙여서 확인",
}


def sample_keys(name: str, cal_mode: CalMode = CalMode.VNA) -> list[str]:
    sample = make_sample(name)
    return keys(sample.sweep, sample.antenna, cal_mode)


def sample_diagnosis(name: str, key: str) -> Diagnosis:
    sample = make_sample(name)
    found = {d.key: d for d in diagnose(context(sample.sweep, sample.antenna))}
    return found[key]


def test_table_covers_every_sample() -> None:
    assert set(EXPECTED) == set(SAMPLE_NAMES)


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_sample_keys_with_vna_calibration(name: str) -> None:
    assert sample_keys(name) == EXPECTED[name]


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_unknown_calibration_appends_uncalibrated_except_for_positive(name: str) -> None:
    extra = [] if name == "positive" else ["uncalibrated"]

    assert sample_keys(name, CalMode.UNKNOWN) == EXPECTED[name] + extra


def test_rules_run_in_spec_order() -> None:
    assert [rule.__name__ for rule in RULES] == RULE_ORDER


@pytest.mark.parametrize(
    ("name", "percent", "verb"),
    [("far_low", "36 %", "줄이는"), ("far_high", "61 %", "늘리는"), ("two_res", "36 %", "늘리는")],
)
def test_length_far_amount_and_direction(name: str, percent: str, verb: str) -> None:
    action = sample_diagnosis(name, "length_far").action

    assert percent in action
    assert verb in action
    assert CAUTION[verb] in action


def test_two_res_uses_the_nearest_resonance_and_reports_the_other() -> None:
    assert "881.2" in sample_diagnosis("two_res", "length_far").evidence
    other = sample_diagnosis("two_res", "other_resonance").evidence
    assert "277.3" in other
    assert "881.2" not in other


def test_offtarget_samples_give_amount_direction_and_caution() -> None:
    long_action = sample_diagnosis("offtarget_low", "too_long").action
    short_action = sample_diagnosis("offtarget_high", "too_short").action

    assert "12 %" in long_action and "줄이는" in long_action
    assert "11 %" in short_action and "늘리는" in short_action
    assert CAUTION["줄이는"] in long_action
    assert CAUTION["늘리는"] in short_action
    assert "자르기 전에" not in short_action
    assert "안테나 도체" in long_action


@pytest.mark.parametrize(
    ("name", "key", "word"),
    [
        ("patch_narrow", "narrow", "기판"),
        ("patch_low_r", "r_low", "가장자리"),
        ("patch_high_r", "r_high", "중심"),
        ("unmatched_low_r", "r_low", "접지판"),
        ("unmatched_high_r", "r_high", "접지"),
        ("narrow", "narrow", "굵게"),
    ],
)
def test_action_depends_on_antenna_kind(name: str, key: str, word: str) -> None:
    assert word in sample_diagnosis(name, key).action


@pytest.mark.parametrize("name", SAMPLE_NAMES)
@pytest.mark.parametrize("cal_mode", list(CalMode))
def test_every_diagnosis_is_complete_and_uses_the_fixed_guide(name: str, cal_mode: CalMode) -> None:
    sample = make_sample(name)

    for found in diagnose(context(sample.sweep, sample.antenna, cal_mode)):
        assert found.title and found.evidence and found.action
        assert found.guide == guide_for(found.key, sample.antenna.kind)
        assert found.guide


def test_positive_s11_hides_everything_else() -> None:
    sweep = magnitude_sweep([0.3, -30.0, 0.0], start=400.0, step=33.0)

    assert keys(sweep, antenna(433.0), CalMode.UNKNOWN) == ["positive_s11"]


def test_any_value_just_above_the_threshold_is_positive() -> None:
    sweep = magnitude_sweep([POSITIVE_S11_DB + 1e-10, -30.0, 0.0], start=400.0, step=33.0)

    assert keys(sweep, antenna(433.0)) == ["positive_s11"]


@pytest.mark.parametrize("first_db", [0.0, 0.1, 0.2])
def test_small_positive_up_to_the_threshold_is_noise(first_db: float) -> None:
    sweep = magnitude_sweep([first_db, -30.0, 0.0], start=400.0, step=33.0)

    assert "positive_s11" not in keys(sweep, antenna(433.0))


def test_positive_threshold_is_two_tenths_of_a_db() -> None:
    assert POSITIVE_S11_DB == 0.2


def test_uncalibrated_action_says_values_are_for_trend_only() -> None:
    sweep = magnitude_sweep([-2.0, -2.5, -2.0])

    found = diagnose(context(sweep, antenna(410.0), CalMode.UNKNOWN))[-1]

    assert found.key == "uncalibrated"
    assert found.action == (
        "수치는 경향 참고용. 교정된 측정으로 다시 확인 "
        "(USB로 받은 값에는 장비의 교정이 반영되지 않는다)"
    )


def test_no_resonance_fallback_when_no_rule_matches() -> None:
    sweep = magnitude_sweep([-2.0, -2.5, -2.0])

    assert keys(sweep, antenna(410.0)) == ["no_resonance"]
    assert keys(sweep, antenna(410.0), CalMode.UNKNOWN) == ["no_resonance", "uncalibrated"]
