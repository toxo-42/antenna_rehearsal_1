"""The 18 synthetic samples and their expected verdicts from spec/p1_core.md.

Expected values come from the spec table. Do not edit them to make a test pass.
"""

from typing import NamedTuple

import pytest

from src.classify import classify
from src.impedance import impedance_at
from src.models import AntennaKind, Stage
from src.synthetic import SAMPLE_NAMES, constant, make_sample, product, rlc

F_TOL = 0.1
DB_TOL = 0.02
PCT_TOL = 0.02
R_TOL = 0.1


class Row(NamedTuple):
    name: str
    target_mhz: float
    stage: str
    f_mhz: float | None = None
    s11_db: float | None = None
    offset_pct: float | None = None
    bandwidth_pct: float | None = None
    others: tuple[float, ...] = ()


ROWS = [
    Row("good", 433, "good", 430.75, -24.71, -0.52, 14.0),
    Row("offtarget_low", 433, "offtarget", 381.25, -25.21, -11.95, 13.89),
    Row("offtarget_high", 433, "offtarget", 480.25, -25.57, 10.91, 13.9),
    Row("narrow", 433, "narrow", 430.75, -20.86, -0.52, 4.81),
    Row("unmatched_low_r", 433, "unmatched", 430.75, -7.35, -0.52, None),
    Row("unmatched_high_r", 433, "unmatched", 430.75, -7.68, -0.52, None),
    Row("far_low", 433, "none", others=(277.3,)),
    Row("far_high", 433, "none", others=(698.05,)),
    Row("open", 433, "none"),
    Row("short", 433, "none"),
    Row("lossy", 433, "none"),
    Row("positive", 433, "none"),
    Row("two_res", 650, "none", others=(881.2, 277.3)),
    Row("third_mode", 433, "unmatched", 430.75, -8.22, -0.52, None, (143.65,)),
    Row("patch_good", 433, "good", 430.75, -20.86, -0.52, 4.81),
    Row("patch_narrow", 433, "narrow", 430.75, -13.96, -0.52, 2.08),
    Row("patch_low_r", 433, "unmatched", 430.75, -7.32, -0.52, None),
    Row("patch_high_r", 433, "unmatched", 430.75, -7.46, -0.52, None),
]

RESISTANCE_AT_RESONANCE = {
    "unmatched_low_r": 20.0,
    "patch_low_r": 20.0,
    "unmatched_high_r": 120.0,
    "patch_high_r": 120.0,
    "third_mode": 22.3,
}


def test_table_covers_every_sample_exactly_once() -> None:
    assert len(ROWS) == 18
    assert sorted(row.name for row in ROWS) == sorted(SAMPLE_NAMES)


def test_only_patch_prefixed_samples_are_patches() -> None:
    kinds = {name: make_sample(name).antenna.kind for name in SAMPLE_NAMES}

    patches = sorted(name for name, kind in kinds.items() if kind is AntennaKind.PATCH)
    assert patches == ["patch_good", "patch_high_r", "patch_low_r", "patch_narrow"]
    assert sum(kind is AntennaKind.MONOPOLE for kind in kinds.values()) == 14


def test_sweep_grid_is_10_to_1000_mhz_in_201_points_with_complex_data() -> None:
    sweep = make_sample("good").sweep

    assert len(sweep.f_mhz) == 201
    assert sweep.f_mhz[0] == pytest.approx(10.0)
    assert sweep.f_mhz[-1] == pytest.approx(1000.0)
    assert sweep.gamma is not None and len(sweep.gamma) == 201
    assert len(sweep.s11_db) == 201


def test_unknown_sample_name_is_rejected() -> None:
    with pytest.raises(KeyError):
        make_sample("nope")


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row.name)
def test_sample_matches_spec_table(row: Row) -> None:
    sample = make_sample(row.name)
    assert sample.antenna.target_mhz == row.target_mhz

    result = classify(sample.sweep, sample.antenna)

    assert result.stage is Stage(row.stage)
    assert [r.f_mhz for r in result.others] == pytest.approx(list(row.others), abs=F_TOL)
    if row.f_mhz is None:
        assert result.selected is None
        assert result.offset_pct is None
        return
    assert result.selected is not None
    assert result.selected.f_mhz == pytest.approx(row.f_mhz, abs=F_TOL)
    assert result.selected.s11_db == pytest.approx(row.s11_db, abs=DB_TOL)
    assert result.offset_pct == pytest.approx(row.offset_pct, abs=PCT_TOL)
    if row.bandwidth_pct is None:
        assert result.selected.bandwidth_pct is None
    else:
        assert result.selected.bandwidth_pct == pytest.approx(row.bandwidth_pct, abs=PCT_TOL)


@pytest.mark.parametrize(("name", "r_ohm"), sorted(RESISTANCE_AT_RESONANCE.items()))
def test_resistance_at_resonance(name: str, r_ohm: float) -> None:
    sample = make_sample(name)
    selected = classify(sample.sweep, sample.antenna).selected
    assert selected is not None

    impedance = impedance_at(sample.sweep, selected.index)

    assert impedance is not None
    assert impedance.r_ohm == pytest.approx(r_ohm, abs=R_TOL)


def test_rlc_is_purely_resistive_at_its_centre_frequency() -> None:
    assert rlc(433.0, 20.0, 8.0)(433.0) == pytest.approx((20.0 - 50.0) / (20.0 + 50.0))
    assert rlc(433.0, 50.0, 8.0)(433.0) == pytest.approx(0.0)
    assert rlc(433.0, 45.0, 8.0)(300.0).imag != 0.0


def test_constant_and_product_builders() -> None:
    assert constant(0.5)(123.0) == 0.5 + 0j
    assert product(constant(0.5), constant(-0.5j))(123.0) == pytest.approx(-0.25j)
