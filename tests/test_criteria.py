"""The stage criteria shown next to the verdict: sentences built from the rule constants."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src import criteria, models
from src.models import AntennaKind, CardStage

ORDER = ["good", "narrow", "offtarget", "unmatched", "none", "invalid"]


def texts(kind: AntennaKind) -> dict[str, str]:
    return {item["stage"]: item["text"] for item in criteria.stage_criteria(kind)}


@pytest.mark.parametrize("kind", list(AntennaKind))
def test_every_card_stage_has_one_sentence_from_good_to_invalid(kind: AntennaKind) -> None:
    items = criteria.stage_criteria(kind)
    assert [item["stage"] for item in items] == ORDER
    assert {item["stage"] for item in items} == {stage.value for stage in CardStage}
    assert all(item["text"].strip() for item in items)


def test_the_bandwidth_number_is_the_one_of_the_antenna_kind() -> None:
    monopole, patch = texts(AntennaKind.MONOPOLE), texts(AntennaKind.PATCH)
    for stage in ("good", "narrow"):
        assert "8 %" in monopole[stage] and "2.5 %" not in monopole[stage]
        assert "2.5 %" in patch[stage] and "8 %" not in patch[stage]
    assert "모노폴" in monopole["narrow"] and "패치" in patch["narrow"]


def test_the_numbers_follow_the_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "MATCH_THRESHOLD_DB", -12.0)
    monkeypatch.setattr(models, "CANDIDATE_WINDOW_PCT", 15.0)
    monkeypatch.setattr(models, "POSITIVE_S11_DB", 0.5)
    monkeypatch.setattr(models, "RESONANCE_MIN_DEPTH_DB", 4.0)
    monkeypatch.setattr(models, "RESONANCE_MAX_S11_DB", -7.0)
    changed = texts(AntennaKind.PATCH)
    for stage in ("good", "narrow", "offtarget", "unmatched"):
        assert "-12 dB" in changed[stage], stage
    assert "±15 %" in changed["none"]
    assert "4 dB" in changed["none"] and "-7 dB" in changed["none"]
    assert "+0.5 dB" in changed["invalid"]


def test_only_the_monopole_mentions_the_conductor_length() -> None:
    assert "길이" in texts(AntennaKind.MONOPOLE)["none"]
    assert "7500" in texts(AntennaKind.MONOPOLE)["none"]
    assert "길이" not in texts(AntennaKind.PATCH)["none"]


def test_the_route_answers_for_each_kind_and_refuses_others(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path / "t.db"))
    for kind in AntennaKind:
        response = client.get("/api/criteria", params={"kind": kind.value})
        assert response.status_code == 200, response.text
        assert response.json() == criteria.stage_criteria(kind)
    refused = client.get("/api/criteria", params={"kind": "dipole"})
    assert refused.status_code == 422
    assert "monopole" in refused.json()["detail"]
