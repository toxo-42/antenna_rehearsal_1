"""Explain and ask on stored measurements over HTTP, the guide list, and parts from the env."""

import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app import create_app
from src.assist import MAX_QUESTION_CHARS, LlmParts, parts_from_env
from src.explain import Explanation, NoExplainer, OllamaExplainer
from src.guides import guide_for
from src.models import Antenna, AntennaKind, Card
from src.ollama import DEFAULT_BASE_URL
from src.router import GUIDE_KEYS, NoRouter, OllamaRouter

OFF = LlmParts(NoExplainer(), NoRouter())


@dataclass
class StubExplainer:
    result: Explanation
    cards: list[Card] = field(default_factory=list)
    antennas: list[Antenna] = field(default_factory=list)

    def explain(self, card: Card, antenna: Antenna) -> Explanation:
        self.cards.append(card)
        self.antennas.append(antenna)
        return self.result


@dataclass
class StubRouter:
    number: int | None
    asked: list[tuple[str, AntennaKind]] = field(default_factory=list)

    def choose(self, question: str, kind: AntennaKind) -> int | None:
        self.asked.append((question, kind))
        return self.number


def number_of(key: str) -> int:
    return GUIDE_KEYS.index(key) + 1


def client_with(tmp_path: Path, parts: LlmParts) -> TestClient:
    return TestClient(create_app(tmp_path / "t.db", parts))


def measured(client: TestClient, sample: str = "offtarget_low", kind: str = "monopole") -> Any:
    antenna = client.post("/api/antennas", json={"name": "a", "kind": kind, "target_mhz": 433.0})
    body = {"antenna_id": antenna.json()["id"], "source": "synthetic", "sample": sample,
            "cal_mode": "vna", "change_note": ""}  # fmt: skip
    response = client.post("/api/measurements", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def ask(client: TestClient, measurement_id: int, question: str) -> Any:
    return client.post(f"/api/measurements/{measurement_id}/ask", json={"question": question})


def test_explain_passes_the_stored_card_and_returns_the_result(tmp_path: Path) -> None:
    stub = StubExplainer(Explanation("ok", "## 글", ("50",), "qwen3.5:4b", 11.2))
    client = client_with(tmp_path, LlmParts(stub, NoRouter()))
    measurement = measured(client)

    response = client.post(f"/api/measurements/{measurement['id']}/explain")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "text": "## 글", "warnings": ["50"],
                               "model": "qwen3.5:4b", "seconds": 11.2}  # fmt: skip
    card = stub.cards[0]
    assert card.headline == measurement["card"]["headline"]
    assert list(card.status) == measurement["card"]["status"]
    assert [d.action for d in card.diagnoses] == [
        d["action"] for d in measurement["card"]["diagnoses"]
    ]
    antenna = stub.antennas[0]
    assert (antenna.kind, antenna.target_mhz) == (AntennaKind.MONOPOLE, 433.0)


def test_explain_when_off(tmp_path: Path) -> None:
    client = client_with(tmp_path, OFF)
    measurement = measured(client)

    response = client.post(f"/api/measurements/{measurement['id']}/explain")

    assert response.json() == {"status": "off", "text": None, "warnings": [],
                               "model": None, "seconds": None}  # fmt: skip


def test_explain_and_ask_on_a_missing_measurement_are_404(tmp_path: Path) -> None:
    client = client_with(tmp_path, OFF)

    assert client.post("/api/measurements/99/explain").status_code == 404
    assert ask(client, 99, "질문").status_code == 404
    assert client.get("/api/measurements/99/guides").status_code == 404


def test_the_card_response_is_the_same_with_the_model_on_or_off(tmp_path: Path) -> None:
    on = LlmParts(OllamaExplainer("m", "http://127.0.0.1:9"), OllamaRouter("m", "x"))
    client = client_with(tmp_path, OFF)
    measurement = measured(client)

    again = client_with(tmp_path, on).get(f"/api/measurements/{measurement['id']}")

    assert again.json() == measurement


def db_dump(db: Path) -> list[str]:
    with closing(sqlite3.connect(db)) as conn:
        return list(conn.iterdump())


def test_the_generated_text_is_not_stored(tmp_path: Path) -> None:
    text = "## 저장되면 안 되는 글"
    stub = StubExplainer(Explanation("ok", text, (), "m", 1.0))
    client = client_with(tmp_path, LlmParts(stub, NoRouter()))
    measurement = measured(client)
    before = db_dump(tmp_path / "t.db")

    assert client.post(f"/api/measurements/{measurement['id']}/explain").json()["text"] == text

    assert db_dump(tmp_path / "t.db") == before
    assert not any("저장되면 안 되는 글" in line for line in before)
    assert client.get(f"/api/measurements/{measurement['id']}").json() == measurement


def test_a_question_linked_to_a_card_item_carries_its_action(tmp_path: Path) -> None:
    router = StubRouter(number_of("too_long"))
    client = client_with(tmp_path, LlmParts(NoExplainer(), router))
    measurement = measured(client)
    action = measurement["card"]["diagnoses"][0]["action"]

    response = ask(client, measurement["id"], "  선이 너무 길면 주파수가 어떻게 돼요?  ")

    assert response.json() == {"status": "matched", "key": "too_long",
                               "guide": guide_for("too_long", AntennaKind.MONOPOLE),
                               "in_card": True, "action": action}  # fmt: skip
    assert router.asked == [("선이 너무 길면 주파수가 어떻게 돼요?", AntennaKind.MONOPOLE)]


def test_a_question_linked_outside_the_card_has_no_action(tmp_path: Path) -> None:
    client = client_with(tmp_path, LlmParts(NoExplainer(), StubRouter(number_of("narrow"))))
    measurement = measured(client, "patch_low_r", "patch")

    body = ask(client, measurement["id"], "주파수 폭이 좁아요").json()

    assert body == {"status": "matched", "key": "narrow",
                    "guide": guide_for("narrow", AntennaKind.PATCH),
                    "in_card": False, "action": None}  # fmt: skip


@pytest.mark.parametrize(
    ("number", "status"), [(0, "none"), (None, "failed")], ids=["none", "failed"]
)
def test_no_link_or_a_failed_link(tmp_path: Path, number: int | None, status: str) -> None:
    client = client_with(tmp_path, LlmParts(NoExplainer(), StubRouter(number)))
    measurement = measured(client)

    body = ask(client, measurement["id"], "오늘 점심 뭐 먹지").json()

    assert body == {"status": status, "key": None, "guide": None, "in_card": False, "action": None}


def test_question_length_is_limited(tmp_path: Path) -> None:
    client = client_with(tmp_path, LlmParts(NoExplainer(), StubRouter(0)))
    measurement_id = measured(client)["id"]

    assert ask(client, measurement_id, "가" * MAX_QUESTION_CHARS).status_code == 200
    too_long = ask(client, measurement_id, "가" * (MAX_QUESTION_CHARS + 1))
    assert too_long.status_code == 422
    assert "200자" in too_long.json()["detail"]
    assert ask(client, measurement_id, "   ").status_code == 422
    assert client.post(f"/api/measurements/{measurement_id}/ask", json={}).status_code == 422


def test_the_guide_list_is_grouped_by_topic_and_marks_card_items(tmp_path: Path) -> None:
    client = client_with(tmp_path, OFF)
    measurement = measured(client)
    card_actions = {d["key"]: d["action"] for d in measurement["card"]["diagnoses"]}

    topics = client.get(f"/api/measurements/{measurement['id']}/guides").json()

    items = [item for topic in topics for item in topic["items"]]
    assert all(topic["topic"] and topic["items"] for topic in topics)
    assert sorted(item["key"] for item in items) == sorted(GUIDE_KEYS)
    for item in items:
        assert item["guide"] == guide_for(item["key"], AntennaKind.MONOPOLE)
        assert item["in_card"] == (item["key"] in card_actions)
        assert item["action"] == card_actions.get(item["key"])


def test_health_reports_which_parts_are_on(tmp_path: Path) -> None:
    on = LlmParts(OllamaExplainer("m", "x"), OllamaRouter("m", "x"))
    only_router = LlmParts(NoExplainer(), OllamaRouter("m", "x"))

    def health(parts: LlmParts) -> Any:
        return client_with(tmp_path, parts).get("/api/health").json()

    assert health(OFF) == {"mode": "local", "ollama": False, "explain": False, "ports": []}
    assert (health(on)["ollama"], health(on)["explain"]) == (True, True)
    assert (health(only_router)["ollama"], health(only_router)["explain"]) == (True, False)


def test_parts_default_to_the_contest_model_on_localhost() -> None:
    parts = parts_from_env({})

    assert isinstance(parts.explainer, OllamaExplainer)
    assert isinstance(parts.router, OllamaRouter)
    assert (parts.explainer.model, parts.explainer.base_url) == ("qwen3.5:4b", DEFAULT_BASE_URL)
    assert (parts.router.model, parts.router.base_url) == ("qwen3.5:4b", DEFAULT_BASE_URL)
    assert DEFAULT_BASE_URL == "http://127.0.0.1:11434"


def test_an_empty_model_turns_both_off() -> None:
    for value in ("", "  "):
        parts = parts_from_env({"OLLAMA_MODEL": value})
        assert isinstance(parts.explainer, NoExplainer)
        assert isinstance(parts.router, NoRouter)


def test_explain_off_keeps_the_router() -> None:
    parts = parts_from_env({"OLLAMA_MODEL": "qwen3.5:9b", "OLLAMA_EXPLAIN": "off"})

    assert isinstance(parts.explainer, NoExplainer)
    assert isinstance(parts.router, OllamaRouter)
    assert parts.router.model == "qwen3.5:9b"
