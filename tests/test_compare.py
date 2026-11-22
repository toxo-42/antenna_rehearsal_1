"""Before/after comparison of two measurements of one antenna (P7)."""

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src import compare, store

CAUSE_WORDS = ("때문", "원인", "덕분", "탓")


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(tmp_path / "t.db"))


def add_antenna(client: TestClient, target: float = 433.0) -> int:
    body = {"name": "a", "kind": "monopole", "target_mhz": target}
    response = client.post("/api/antennas", json=body)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def measure(client: TestClient, antenna_id: int, sample: str, note: str = "") -> int:
    body = {"antenna_id": antenna_id, "source": "synthetic", "sample": sample,
            "cal_mode": "vna", "change_note": note}  # fmt: skip
    response = client.post("/api/measurements", json=body)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def get_compare(client: TestClient, before: int, after: int) -> Any:
    return client.get(f"/api/compare?before={before}&after={after}")


def row(**values: Any) -> dict[str, Any]:
    base = {"id": 1, "stage": "offtarget", "resonance_mhz": 400.0, "s11_db": -20.0,
            "bandwidth_pct": 10.0, "change_note": ""}  # fmt: skip
    return {**base, **values}


# --- through the API -------------------------------------------------------------------------


def test_offtarget_low_to_good_moves_up_and_gets_closer(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    before = measure(client, antenna_id, "offtarget_low")
    after = measure(client, antenna_id, "good", note="도체 줄임 5 mm")
    response = get_compare(client, before, after)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verdict"] == compare.CLOSER == "가까워짐"
    assert body["comparable"] is True
    assert body["shift_mhz"] == pytest.approx(49.5)
    assert body["distance_before_mhz"] == pytest.approx(51.75)
    assert body["distance_after_mhz"] == pytest.approx(2.25)
    assert body["distance_change_mhz"] == pytest.approx(-49.5)
    assert body["step_mhz"] == pytest.approx(4.95)
    assert body["target_mhz"] == 433.0
    assert body["stage"] == {"before": "offtarget", "after": "good"}
    assert body["change_note"] == "도체 줄임 5 mm"
    assert body["reasons"] == []


def test_s11_and_bandwidth_changes_are_after_minus_before(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    before_id = measure(client, antenna_id, "offtarget_low")
    after_id = measure(client, antenna_id, "good")
    before = client.get(f"/api/measurements/{before_id}").json()
    after = client.get(f"/api/measurements/{after_id}").json()
    body = get_compare(client, before_id, after_id).json()
    assert body["s11_change_db"] == pytest.approx(after["s11_db"] - before["s11_db"])
    expected_bw = after["bandwidth_pct"] - before["bandwidth_pct"]
    assert body["bandwidth_change_pct"] == pytest.approx(expected_bw)


def test_good_to_offtarget_low_gets_farther(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    before = measure(client, antenna_id, "good")
    after = measure(client, antenna_id, "offtarget_low", note="도체 늘림 5 mm")
    body = get_compare(client, before, after).json()
    assert body["verdict"] == compare.FARTHER == "멀어짐"
    assert body["shift_mhz"] == pytest.approx(-49.5)
    assert body["distance_change_mhz"] == pytest.approx(49.5)


def test_same_measurement_shows_no_difference(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    only = measure(client, antenna_id, "good")
    body = get_compare(client, only, only).json()
    assert body["verdict"] == compare.SAME == "차이 없음(측정 간격 이내)"
    assert body["shift_mhz"] == 0.0
    assert body["distance_change_mhz"] == 0.0


def test_measurement_without_resonance_cannot_be_compared(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    before = measure(client, antenna_id, "open")
    after = measure(client, antenna_id, "good")
    body = get_compare(client, before, after).json()
    assert body["verdict"] == compare.NOT_COMPARABLE == "비교 불가"
    assert body["comparable"] is False
    assert len(body["reasons"]) == 1
    assert body["reasons"][0].startswith(f"이전 측정({before}번)")
    assert "목표 근처의 공진이 없습니다" in body["reasons"][0]
    for key in compare.NUMBER_KEYS:
        assert body[key] is None, key
    assert body["step_mhz"] is None
    assert body["stage"] == {"before": "none", "after": "good"}


def test_invalid_measurement_cannot_be_compared(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    before = measure(client, antenna_id, "good")
    after = measure(client, antenna_id, "positive")
    body = get_compare(client, before, after).json()
    assert body["verdict"] == compare.NOT_COMPARABLE
    assert any(
        reason.startswith(f"이후 측정({after}번)") and "invalid" in reason
        for reason in body["reasons"]
    )


def test_after_without_resonance_or_before_invalid_also_blocks(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    good = measure(client, antenna_id, "good")
    no_resonance = measure(client, antenna_id, "open")
    invalid = measure(client, antenna_id, "positive")
    after_side = get_compare(client, good, no_resonance).json()
    assert after_side["verdict"] == compare.NOT_COMPARABLE
    assert after_side["reasons"][0].startswith(f"이후 측정({no_resonance}번)")
    before_side = get_compare(client, invalid, good).json()
    assert before_side["verdict"] == compare.NOT_COMPARABLE
    assert any(r.startswith(f"이전 측정({invalid}번)") for r in before_side["reasons"])


def test_measurements_of_different_antennas_are_refused(client: TestClient) -> None:
    first = measure(client, add_antenna(client), "offtarget_low")
    second = measure(client, add_antenna(client), "good")
    response = get_compare(client, first, second)
    assert response.status_code == 422
    assert "같은 안테나" in response.json()["detail"]


def test_missing_measurement_is_not_found(client: TestClient) -> None:
    only = measure(client, add_antenna(client), "good")
    assert get_compare(client, only, 999).status_code == 404
    assert get_compare(client, 999, only).status_code == 404
    assert get_compare(client, only, 2**63).status_code == 404


def test_missing_query_parameter_is_422(client: TestClient) -> None:
    assert client.get("/api/compare?before=1").status_code == 422


def test_summary_states_the_change_and_result_without_a_cause(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    before = measure(client, antenna_id, "offtarget_low")
    after = measure(client, antenna_id, "good", note="도체 줄임 5 mm")
    summary = get_compare(client, before, after).json()["summary"]
    assert "도체 줄임 5 mm" in summary
    assert "+49.50 MHz" in summary and "가까워짐" in summary
    assert not any(word in summary for word in CAUSE_WORDS)


def test_a_free_text_note_is_kept_out_of_the_summary(client: TestClient) -> None:
    antenna_id = add_antenna(client)
    before = measure(client, antenna_id, "offtarget_low")
    after = measure(client, antenna_id, "good", note="케이블 때문에 개선됐다")
    body = get_compare(client, before, after).json()
    assert body["change_note"] == "케이블 때문에 개선됐다"  # the record itself is unchanged
    assert "케이블" not in body["summary"]
    assert "선택 상자 형식이 아니" in body["summary"]
    assert not any(word in body["summary"] for word in CAUSE_WORDS)


def test_a_measurement_compared_with_itself_is_not_called_a_new_measurement(
    client: TestClient,
) -> None:
    only = measure(client, add_antenna(client), "good", note="도체 줄임 5 mm")
    summary = get_compare(client, only, only).json()["summary"]
    assert summary == f"같은 측정({only}번)끼리 비교했습니다: {compare.SAME}."


# --- the rules on their own ------------------------------------------------------------------


def test_distance_change_smaller_than_one_step_is_no_difference() -> None:
    assert compare.distance_verdict(-4.9, 4.95) == compare.SAME
    assert compare.distance_verdict(4.9, 4.95) == compare.SAME
    assert compare.distance_verdict(0.0, 4.95) == compare.SAME


def test_distance_change_of_one_step_or_more_has_a_direction() -> None:
    assert compare.distance_verdict(-4.95, 4.95) == compare.CLOSER
    assert compare.distance_verdict(4.95, 4.95) == compare.FARTHER
    # 381.25 - 376.3 lands a hair under one step in floating point; it still counts as one step.
    assert compare.distance_verdict(381.25 - 376.3, 4.95) == compare.FARTHER


def sweep_json(freqs: list[float]) -> str:
    return json.dumps([[f * 1e6, -1.0, None, None] for f in freqs])


def test_local_step_is_the_coarser_gap_beside_the_resonance_point() -> None:
    sweep = sweep_json([100.0, 102.0, 106.0, 114.0])
    assert compare.local_step_mhz(sweep, 102.0) == pytest.approx(4.0)
    assert compare.local_step_mhz(sweep, 103.0) == pytest.approx(4.0)  # nearest point is 102
    assert compare.local_step_mhz(sweep, 100.0) == pytest.approx(2.0)  # first point: one gap
    assert compare.local_step_mhz(sweep, 114.0) == pytest.approx(8.0)  # last point: one gap


def test_pair_step_uses_the_coarser_side() -> None:
    fine = {"sweep_json": sweep_json([429.0, 430.0, 431.0]), "resonance_mhz": 430.0}
    coarse = {"sweep_json": sweep_json([425.0, 430.0, 435.0]), "resonance_mhz": 430.0}
    assert compare.pair_step_mhz(fine, coarse) == pytest.approx(5.0)
    assert compare.pair_step_mhz(coarse, fine) == pytest.approx(5.0)


def stored_pair(
    db: Path, sweeps: tuple[list[float], list[float]], resonances: tuple[float, float]
) -> list[int]:
    """Two measurements of one 433 MHz antenna, with the given sweep and resonance each."""
    store.init_db(db)
    ids = []
    with store.connect(db) as conn:
        antenna_id = store.insert_antenna(conn, "a", "monopole", 433.0)
        for freqs, resonance in zip(sweeps, resonances, strict=True):
            new = store.NewMeasurement(antenna_id, "2026-01-01T00:00:00", "csv", "vna", "offtarget",
                                       resonance, -20.0, 10.0, sweep_json(freqs), "{}", "")  # fmt: skip
            ids.append(store.insert_measurement(conn, new))
    return ids


def uniform(step: float) -> list[float]:
    return [425.0 + i * step for i in range(20)]


def test_a_sweep_dense_only_near_the_resonance_uses_its_local_spacing(tmp_path: Path) -> None:
    # 1 MHz between 425 and 440, 100 MHz outside: the mean spacing would be about 12 MHz.
    freqs = [100.0, 200.0, 300.0, *(425.0 + i for i in range(16)), 600.0, 700.0, 800.0]
    before, after = stored_pair(tmp_path / "t.db", (freqs, freqs), (430.0, 432.0))
    result = compare.compare_measurements(tmp_path / "t.db", before, after)
    assert result["step_mhz"] == pytest.approx(1.0)
    assert result["verdict"] == compare.CLOSER


@pytest.mark.parametrize("steps", [(1.0, 5.0), (5.0, 1.0)])
def test_comparison_allows_for_the_coarser_of_the_two_sweeps(
    tmp_path: Path, steps: tuple[float, float]
) -> None:
    sweeps = (uniform(steps[0]), uniform(steps[1]))
    before, after = stored_pair(tmp_path / "t.db", sweeps, (430.0, 432.0))
    result = compare.compare_measurements(tmp_path / "t.db", before, after)
    assert result["step_mhz"] == pytest.approx(5.0)
    assert result["verdict"] == compare.SAME
