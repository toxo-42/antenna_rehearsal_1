"""A monopole with its conductor length: the resonance is picked near the expected frequency
(7500 / length in cm), and a missing one is not turned into length advice."""

from pathlib import Path

import pytest

from src.classify import classify
from src.models import Antenna, AntennaKind, CalMode, Stage, Sweep
from src.sweep_parser import parse_sweep_csv
from src.verdict import HEADLINES, build_card
from tests.diag_helpers import dip_sweep, find, keys, magnitude_sweep

DATA = Path(__file__).resolve().parent / "data"
MONOPOLE, PATCH = AntennaKind.MONOPOLE, AntennaKind.PATCH
LENGTH_200 = 37.5  # 7500 / 37.5 = 200 MHz


def antenna(target: float, length_cm: float | None, kind: AntennaKind = MONOPOLE) -> Antenna:
    return Antenna(name="t", kind=kind, target_mhz=target, length_cm=length_cm)


def dips(values: dict[float, float]) -> Sweep:
    return dip_sweep(values, start=100.0, stop=800.0)


def test_expected_frequency_is_a_quarter_wave_for_monopoles_only() -> None:
    assert antenna(433.0, 12.0).expected_mhz == pytest.approx(625.0)
    assert antenna(433.0, None).expected_mhz is None
    assert antenna(433.0, 12.0, PATCH).expected_mhz is None


def test_the_resonance_nearest_the_expected_frequency_is_selected() -> None:
    sweep = dips({200.0: -20.0, 300.0: -20.0})

    assert classify(sweep, antenna(300.0, None)).selected.f_mhz == 300.0  # type: ignore[union-attr]
    result = classify(sweep, antenna(300.0, LENGTH_200))
    assert result.selected is not None and result.selected.f_mhz == 200.0
    assert result.offset_pct == pytest.approx(-100 / 3)  # still measured from the target
    assert [r.f_mhz for r in result.others] == [300.0]


@pytest.mark.parametrize(("f_mhz", "stage"), [(220.0, Stage.OFFTARGET), (230.0, Stage.NONE)])
def test_the_window_is_ten_percent_around_the_expected_frequency(
    f_mhz: float, stage: Stage
) -> None:
    assert classify(dips({f_mhz: -20.0}), antenna(200.0, LENGTH_200)).stage is stage


def test_a_band_that_holds_the_expected_frequency_wins_over_a_nearer_dip() -> None:
    # 180~200 MHz is one matched band (lowest at 180); the single dip at 215 is nearer to 200.
    values = {180.0: -20.0, 185.0: -18.0, 190.0: -15.0, 195.0: -13.0, 200.0: -12.0, 215.0: -20.0}
    sweep = dip_sweep(values, start=100.0, stop=400.0, step=5.0)

    result = classify(sweep, antenna(200.0, LENGTH_200))

    assert result.selected is not None and result.selected.f_mhz == 180.0


def test_a_patch_ignores_the_length() -> None:
    sweep = dips({200.0: -20.0, 300.0: -20.0})

    result = classify(sweep, antenna(300.0, LENGTH_200, PATCH))

    assert result.selected is not None and result.selected.f_mhz == 300.0


def test_measured_12cm_built_for_433_is_told_to_lengthen() -> None:
    sweep = parse_sweep_csv((DATA / "monopole_12cm.csv").read_text(encoding="utf-8"))
    ant = antenna(433.0, 12.0)

    assert keys(sweep, antenna(433.0, None)) == ["length_far", "other_resonance"]  # as before
    assert keys(sweep, ant) == ["too_short", "match_unknown", "common_mode"]
    assert "약 44 % 늘리는" in find(sweep, ant, "too_short").action


def test_only_a_weak_dip_where_the_resonance_should_be() -> None:
    sweep, ant = dips({200.0: -4.0, 400.0: -20.0}), antenna(200.0, LENGTH_200)

    assert keys(sweep, antenna(200.0, None)) == ["length_far"]
    assert keys(sweep, ant) == ["weak_fundamental"]
    found = find(sweep, ant, "weak_fundamental")
    assert "길이 37.5 cm" in found.evidence and "예상 공진 200.00 MHz" in found.evidence
    assert "얕은 딥 200.00 MHz" in found.evidence
    assert "길이는 아직 바꾸지 말 것" in found.action


def test_nothing_where_the_resonance_should_be_is_not_a_length_error() -> None:
    sweep, ant = dips({400.0: -20.0}), antenna(200.0, LENGTH_200)

    assert keys(sweep, ant) == ["missing_fundamental"]
    found = find(sweep, ant, "missing_fundamental")
    assert "길이 37.5 cm" in found.evidence and "180~220 MHz" in found.evidence
    assert "급전부" in found.action and "접지" in found.action
    assert "늘리는" not in found.action and "줄이는" not in found.action
    card = build_card(sweep, ant, CalMode.VNA)
    assert card.headline == "이 길이라면 있어야 할 공진이 보이지 않습니다"
    assert card.headline != HEADLINES[card.stage]


def test_an_expected_frequency_outside_the_sweep_asks_for_a_wider_range() -> None:
    sweep, ant = dips({400.0: -20.0}), antenna(400.0, 7.5)  # expected 1000 MHz, sweep ends at 800

    found = find(sweep, ant, "missing_fundamental")

    assert "측정 범위" in found.action and "1000" in found.action
    assert "급전부" not in found.action


def test_a_dead_feed_is_reported_once() -> None:
    sweep = magnitude_sweep([0.0] * 41, start=100.0, step=10.0)

    assert keys(sweep, antenna(200.0, LENGTH_200)) == ["feed_fault"]


def test_status_shows_the_expected_frequency_and_the_length() -> None:
    sweep = dips({200.0: -20.0})

    with_length = build_card(sweep, antenna(200.0, LENGTH_200), CalMode.VNA).status
    without = build_card(sweep, antenna(200.0, None), CalMode.VNA).status
    missing = build_card(dips({400.0: -20.0}), antenna(200.0, LENGTH_200), CalMode.VNA).status

    assert "예상 공진 200.00 MHz (도체 길이 37.5 cm)" in with_length
    assert not any("예상" in line for line in without)
    assert missing[0] == "예상 주파수 근처에 공진 없음"
