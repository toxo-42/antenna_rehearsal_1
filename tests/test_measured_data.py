"""Measured sweeps in tests/data/ and their expected verdicts from spec/p1_core.md and
spec/p2_diagnosis.md.

Expected values come from the spec tables. Do not edit them to make a test pass.
"""

from pathlib import Path
from typing import NamedTuple

import pytest

from src.classify import classify
from src.diagnosis import context_for, diagnose
from src.impedance import impedance_at
from src.models import Antenna, AntennaKind, CalMode, Stage, Sweep
from src.sweep_parser import parse_sweep_csv
from src.verdict import build_card

DATA = Path(__file__).resolve().parent / "data"
F_TOL = 0.1
DB_TOL = 0.02
PCT_TOL = 0.02
OHM_TOL = 0.1

MONOPOLE = AntennaKind.MONOPOLE
PATCH = AntennaKind.PATCH


class Row(NamedTuple):
    file: str
    kind: AntennaKind
    target_mhz: float
    stage: str
    f_mhz: float | None = None
    s11_db: float | None = None
    offset_pct: float | None = None
    bandwidth_pct: float | None = None
    others: tuple[float, ...] = ()


ROWS = [
    Row("monopole_5cm.csv", MONOPOLE, 1350, "good", 1355.5, -19.91, 0.41, 17.08),
    Row("monopole_11.5cm.csv", MONOPOLE, 650, "unmatched", 652.85, -8.95, 0.44, None),
    Row("monopole_12cm.csv", MONOPOLE, 625, "unmatched", 622.95, -8.59, -0.33, None),
    Row("monopole_12cm.csv", MONOPOLE, 433, "none", others=(622.95, 1833.9)),
    Row("monopole_14cm.csv", MONOPOLE, 535, "narrow", 538.23, -10.30, 0.60, 2.12),
    Row("saa2_patch_2450.csv", PATCH, 2450, "good", 2445.0, -30.35, -0.20, 3.59),
]

KEY_ORDER = [
    (ROWS[0], "good", ["other_resonance", "good"]),
    (ROWS[1], "unmatched", ["match_unknown", "common_mode", "other_resonance"]),
    (ROWS[2], "unmatched", ["match_unknown", "common_mode", "other_resonance"]),
    (ROWS[3], "none", ["length_far", "other_resonance"]),
    (ROWS[4], "narrow", ["other_resonance", "narrow"]),
    (ROWS[5], "good", ["good"]),
]


def row_id(row: Row) -> str:
    return f"{row.file}@{row.target_mhz:g}"


KEY_IDS = [row_id(row) for row, _, _ in KEY_ORDER]


def load(name: str) -> Sweep:
    return parse_sweep_csv((DATA / name).read_text(encoding="utf-8"))


def antenna_for(row: Row) -> Antenna:
    return Antenna(name=row.file, kind=row.kind, target_mhz=row.target_mhz)


def test_monopole_files_have_magnitude_only_and_saa2_has_complex() -> None:
    for name in ("monopole_5cm.csv", "monopole_11.5cm.csv", "monopole_12cm.csv"):
        assert load(name).gamma is None
    assert load("monopole_14cm.csv").gamma is None
    assert load("saa2_patch_2450.csv").gamma is not None


def test_monopole_14cm_has_1501_points() -> None:
    assert len(load("monopole_14cm.csv").f_mhz) == 1501


@pytest.mark.parametrize("row", ROWS, ids=row_id)
def test_measured_file_matches_the_spec_row(row: Row) -> None:
    result = classify(load(row.file), antenna_for(row))

    assert result.stage == Stage(row.stage)
    assert [r.f_mhz for r in result.others][: len(row.others)] == pytest.approx(
        list(row.others), abs=F_TOL
    )
    if row.f_mhz is None:
        assert result.selected is None
        return
    assert result.selected is not None
    assert result.selected.f_mhz == pytest.approx(row.f_mhz, abs=F_TOL)
    assert result.selected.s11_db == pytest.approx(row.s11_db, abs=DB_TOL)
    assert result.offset_pct == pytest.approx(row.offset_pct, abs=PCT_TOL)
    if row.bandwidth_pct is None:
        assert result.selected.bandwidth_pct is None
    else:
        assert result.selected.bandwidth_pct == pytest.approx(row.bandwidth_pct, abs=PCT_TOL)


def test_none_row_lists_exactly_the_two_other_resonances_in_order() -> None:
    row = ROWS[3]

    others = classify(load(row.file), antenna_for(row)).others

    assert [r.f_mhz for r in others] == pytest.approx(list(row.others), abs=F_TOL)


def test_saa2_patch_impedance_at_resonance() -> None:
    row = ROWS[5]
    sweep = load(row.file)
    selected = classify(sweep, antenna_for(row)).selected
    assert selected is not None

    impedance = impedance_at(sweep, selected.index)

    assert impedance is not None
    assert impedance.r_ohm == pytest.approx(52.5, abs=OHM_TOL)
    assert impedance.x_ohm == pytest.approx(1.8, abs=OHM_TOL)


@pytest.mark.parametrize(("row", "card_stage", "expected"), KEY_ORDER, ids=KEY_IDS)
def test_measured_card_stage_and_key_order(row: Row, card_stage: str, expected: list[str]) -> None:
    sweep, ant = load(row.file), antenna_for(row)

    card = build_card(sweep, ant, CalMode.VNA)

    assert card.stage.value == card_stage
    assert [d.key for d in card.diagnoses] == expected


@pytest.mark.parametrize(("row", "card_stage", "expected"), KEY_ORDER, ids=KEY_IDS)
def test_unknown_calibration_appends_uncalibrated_to_measured_files(
    row: Row, card_stage: str, expected: list[str]
) -> None:
    sweep, ant = load(row.file), antenna_for(row)

    card = build_card(sweep, ant, CalMode.UNKNOWN)

    assert card.stage.value == card_stage
    assert [d.key for d in card.diagnoses] == [*expected, "uncalibrated"]
    assert [d.key for d in diagnose(context_for(sweep, ant, CalMode.UNKNOWN))] == [
        *expected,
        "uncalibrated",
    ]
