"""Comparison of two stored rows without a database: distance, step, blocking, summary."""

import pytest

from src import compare
from tests.test_compare import row


def test_distance_to_the_target_has_no_sign() -> None:
    above = compare.compare_rows(
        row(resonance_mhz=445.0), row(id=2, resonance_mhz=438.0), 433.0, 5.0
    )
    assert above["distance_before_mhz"] == pytest.approx(12.0)
    assert above["distance_after_mhz"] == pytest.approx(5.0)
    assert above["verdict"] == compare.CLOSER
    crossing = compare.compare_rows(
        row(resonance_mhz=440.0), row(id=2, resonance_mhz=426.0), 433.0, 5.0
    )
    assert crossing["shift_mhz"] == pytest.approx(-14.0)
    assert crossing["distance_change_mhz"] == pytest.approx(0.0)
    assert crossing["verdict"] == compare.SAME


def test_step_decides_between_no_difference_and_a_direction() -> None:
    before = row(resonance_mhz=430.0)
    after = row(id=2, resonance_mhz=432.0)
    assert compare.compare_rows(before, after, 433.0, 1.0)["verdict"] == compare.CLOSER
    assert compare.compare_rows(before, after, 433.0, 5.0)["verdict"] == compare.SAME


def test_both_sides_can_block_and_each_reason_is_listed() -> None:
    before = row(stage="none", resonance_mhz=None, s11_db=None, bandwidth_pct=None)
    after = row(id=2, stage="invalid")
    result = compare.compare_rows(before, after, 433.0, 5.0)
    assert result["verdict"] == compare.NOT_COMPARABLE
    assert len(result["reasons"]) == 2
    assert result["summary"].startswith("비교 불가")


def test_missing_bandwidth_on_one_side_leaves_only_that_change_empty() -> None:
    result = compare.compare_rows(row(bandwidth_pct=None), row(id=2), 433.0, 5.0)
    assert result["comparable"] is True
    assert result["bandwidth_change_pct"] is None
    assert result["s11_change_db"] == 0.0


def test_summary_without_a_note_says_no_change_was_recorded() -> None:
    result = compare.compare_rows(row(), row(id=2, resonance_mhz=420.0), 433.0, 5.0)
    assert result["summary"].startswith("이후 측정(2번)에 기록된 변경이 없습니다.")
    assert "다시 잰" not in result["summary"]
