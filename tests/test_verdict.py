"""The verdict card: stage, headline, status lines, and its serialized shape."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from src.classify import classify
from src.models import AntennaKind, CalMode, Card, CardStage, Sweep
from src.synthetic import SAMPLE_NAMES, make_sample
from src.verdict import build_card
from tests.diag_helpers import antenna, magnitude_sweep

CONTRACT = Path(__file__).resolve().parent.parent / "contract" / "measurement.json"


def sample_card(name: str, cal_mode: CalMode = CalMode.VNA) -> Card:
    sample = make_sample(name)
    return build_card(sample.sweep, sample.antenna, cal_mode)


def lines_with(card: Card, word: str) -> list[str]:
    return [line for line in card.status if word in line]


@pytest.mark.parametrize("name", [n for n in SAMPLE_NAMES if n != "positive"])
def test_card_stage_is_the_p1_stage(name: str) -> None:
    sample = make_sample(name)

    assert sample_card(name).stage == classify(sample.sweep, sample.antenna).stage.value


def test_positive_s11_makes_the_card_invalid_even_when_p1_says_good() -> None:
    sweep = magnitude_sweep([0.1, -30.0, 0.0], start=400.0, step=33.0)
    ant = antenna(433.0, AntennaKind.PATCH)
    good = build_card(magnitude_sweep([0.0, -30.0, 0.0], start=400.0, step=33.0), ant, CalMode.VNA)
    assert good.stage is CardStage.GOOD

    card = build_card(sweep, ant, CalMode.VNA)

    assert card.stage is CardStage.INVALID
    assert [d.key for d in card.diagnoses] == ["positive_s11"]
    assert card.headline != good.headline
    assert "판정할 수 없" in card.headline


def test_positive_sample_is_invalid() -> None:
    assert sample_card("positive").stage is CardStage.INVALID


def test_each_stage_has_its_own_headline() -> None:
    names = ("good", "narrow", "offtarget_low", "unmatched_low_r", "far_low", "positive")
    headlines = {sample_card(name).stage: sample_card(name).headline for name in names}

    assert set(headlines) == set(CardStage)
    assert len(set(headlines.values())) == len(CardStage)
    assert all(headlines.values())
    assert sample_card("offtarget_high").headline == headlines[CardStage.OFFTARGET]


def test_band_edge_headline_does_not_say_the_resonance_misses_the_target() -> None:
    # Resonance 420 MHz exactly on the target; the band's low edge is 1.67 MHz away.
    sweep = magnitude_sweep([0, -5, -11, -10.5, -10.5, -10.2, 0], start=400.0)

    card = build_card(sweep, antenna(420.0, AntennaKind.PATCH), CalMode.VNA)

    assert card.stage is CardStage.OFFTARGET
    assert [d.key for d in card.diagnoses] == ["band_edge"]
    assert card.headline != sample_card("offtarget_low").headline
    assert "대역 끝" in card.headline


def test_status_of_a_matched_resonance() -> None:
    card = sample_card("offtarget_low")

    assert card.status[0] == "공진 381.25 MHz (목표 -51.75 MHz, -11.95 %)"
    assert lines_with(card, "S11") == ["S11 -25.21 dB (깊이 25.06 dB)"]
    assert lines_with(card, "대역") == ["대역 354.42~407.38 MHz (폭 13.89 %)"]
    assert len(lines_with(card, "공진점 R")) == 1
    assert lines_with(card, "측정 간격") == ["측정 간격 4.95 MHz"]


def test_status_shows_a_positive_offset_with_a_plus_sign() -> None:
    assert sample_card("offtarget_high").status[0] == "공진 480.25 MHz (목표 +47.25 MHz, +10.91 %)"


def test_status_shows_impedance_at_the_resonance() -> None:
    card = sample_card("unmatched_low_r")  # rlc(433, 20, 8) sampled at 430.75 MHz

    assert lines_with(card, "공진점 R") == ["공진점 R 20.00 Ω, X -1.67 Ω"]


def test_status_without_a_selected_resonance_says_so_and_hides_the_far_one() -> None:
    card = sample_card("far_low")

    assert card.status[0] == "목표 근처에 공진 없음"
    assert lines_with(card, "277") == []
    assert lines_with(card, "S11") == []
    assert lines_with(card, "대역") == []
    assert lines_with(card, "공진점 R") == []
    assert "277.3" in card.diagnoses[0].evidence


def test_unmatched_status_has_no_band_line() -> None:
    assert lines_with(sample_card("unmatched_low_r"), "대역") == []


def test_magnitude_only_status_has_no_impedance_line() -> None:
    sweep = magnitude_sweep([0, 0, -5, -15, -30, -15, -5, 0, 0, 0, 0], start=380.0)

    card = build_card(sweep, antenna(428.0, AntennaKind.PATCH), CalMode.VNA)

    assert card.stage is CardStage.GOOD
    assert lines_with(card, "공진점 R") == []
    assert lines_with(card, "측정 간격") == ["측정 간격 10.00 MHz"]


@pytest.mark.parametrize("dip_db", [-20.0, -8.0])
def test_reflection_of_exactly_one_has_no_impedance_line_or_inf_text(dip_db: float) -> None:
    gamma = (0.5 + 0j,) * 3 + (1 + 0j,) + (0.5 + 0j,) * 3
    sweep = Sweep(
        f_mhz=tuple(420.0 + 5 * i for i in range(7)),
        s11_db=(-1.0, -2.0, -4.0, dip_db, -4.0, -2.0, -1.0),
        gamma=gamma,
    )

    card = build_card(sweep, antenna(435.0), CalMode.VNA)
    texts = [*card.status, *(t for d in card.diagnoses for t in (d.evidence, d.action))]

    assert lines_with(card, "공진점 R") == []
    assert [t for t in texts if "inf" in t or "nan" in t] == []


def test_status_shows_the_calibration_state() -> None:
    vna = lines_with(sample_card("good", CalMode.VNA), "교정")
    unknown = lines_with(sample_card("good", CalMode.UNKNOWN), "교정")

    assert len(vna) == 1 and len(unknown) == 1
    assert vna != unknown


def test_uneven_spacing_is_shown_as_a_range() -> None:
    freqs = (400.0, 410.0, 420.0, 430.0, 440.0, 450.0, 460.0, 470.0, 480.0, 1000.0)
    values = (0.0, -5.0, -15.0, -30.0, -15.0, -5.0, 0.0, 0.0, 0.0, 0.0)

    card = build_card(Sweep(f_mhz=freqs, s11_db=values), antenna(432.0), CalMode.VNA)

    assert lines_with(card, "측정 간격") == ["측정 간격 10.00~520.00 MHz"]


@pytest.mark.parametrize("name", SAMPLE_NAMES)
def test_serialized_card_has_the_contract_keys(name: str) -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))["card"]

    card = asdict(sample_card(name, CalMode.UNKNOWN))

    assert list(card) == list(contract)
    assert isinstance(card["stage"], str) and isinstance(card["headline"], str)
    assert card["status"] and all(isinstance(line, str) for line in card["status"])
    assert card["diagnoses"]
    for diagnosis in card["diagnoses"]:
        assert list(diagnosis) == list(contract["diagnoses"][0])
        assert all(isinstance(value, str) for value in diagnosis.values())
    json.dumps(card, allow_nan=False)
