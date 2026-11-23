"""OllamaRouter against a fake HTTP server, the numbered prompt, and answer parsing."""

import pytest

from src.guides import GUIDES, guide_for
from src.models import AntennaKind
from src.router import (
    GUIDE_KEYS,
    ROUTE_OPTIONS,
    TOPICS,
    NoRouter,
    OllamaRouter,
    build_route_prompt,
    key_for,
    parse_choice,
)
from tests.fake_ollama import closed_port_url, fake_ollama, record_timeouts

MONOPOLE = AntennaKind.MONOPOLE
PATCH = AntennaKind.PATCH


def test_there_are_24_guides_numbered_in_table_order() -> None:
    assert len(GUIDE_KEYS) == 24
    assert GUIDE_KEYS == tuple(GUIDES)
    assert key_for(1) == "positive_s11"
    assert key_for(24) == "uncalibrated"
    assert key_for(0) is None


def test_every_guide_belongs_to_exactly_one_topic() -> None:
    keys = [key for _, topic_keys in TOPICS for key in topic_keys]

    assert sorted(keys) == sorted(GUIDE_KEYS)


@pytest.mark.parametrize("kind", [MONOPOLE, PATCH])
def test_the_prompt_lists_the_guides_for_the_antenna_kind(kind: AntennaKind) -> None:
    prompt = build_route_prompt("선이 길면?", kind)

    assert prompt.startswith("아래 설명 목록에서 학생 질문과 가장 관련 있는 설명 번호 하나만")
    assert "\n\n설명 목록:\n1. " + guide_for("positive_s11", kind) + "\n" in prompt
    for number, key in enumerate(GUIDE_KEYS, start=1):
        assert f"\n{number}. {guide_for(key, kind)}\n" in prompt
    assert prompt.endswith("\n\n학생 질문: 선이 길면?\n번호:")


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("7", 7), (" 12\n", 12), ("번호: 3", 3), ("0", 0), ("24", 24), ("05", 5)],
)
def test_one_number_in_range_is_used(answer: str, expected: int) -> None:
    assert parse_choice(answer) == expected


@pytest.mark.parametrize(
    "answer", ["", "3, 5", "25", "100", "관련 설명이 없습니다", "1 2", "-1", "-0", "번호: -5"]
)
def test_anything_else_is_a_failed_link(answer: str) -> None:
    assert parse_choice(answer) is None


def test_a_number_answer_is_returned_and_the_request_follows_the_spec() -> None:
    with fake_ollama("6") as fake:
        assert OllamaRouter("qwen3.5:4b", fake.base_url).choose("선이 길면?", MONOPOLE) == 6

    body = fake.requests[0]
    assert fake.paths == ["/api/generate"]
    assert body["prompt"] == build_route_prompt("선이 길면?", MONOPOLE)
    assert (body["stream"], body["think"], body["keep_alive"]) == (False, False, "10m")
    assert body["options"] == ROUTE_OPTIONS == {"num_ctx": 4096, "num_predict": 6, "temperature": 0}
    assert "format" not in body


def test_zero_means_no_related_guide() -> None:
    with fake_ollama("0") as fake:
        assert OllamaRouter("m", fake.base_url).choose("점심 뭐 먹지", MONOPOLE) == 0


@pytest.mark.parametrize("answer", ["3 그리고 5", "관련된 설명은 길이에 관한 것입니다"])
def test_two_numbers_or_a_sentence_fail(answer: str) -> None:
    with fake_ollama(answer) as fake:
        assert OllamaRouter("m", fake.base_url).choose("질문", MONOPOLE) is None


def test_a_body_cut_short_fails() -> None:
    with fake_ollama("6", extra_length=50) as fake:
        assert OllamaRouter("m", fake.base_url).choose("질문", MONOPOLE) is None


def test_a_refused_connection_fails() -> None:
    assert OllamaRouter("m", closed_port_url()).choose("질문", MONOPOLE) is None


def test_a_timeout_fails() -> None:
    with fake_ollama("6", delay_s=1.0) as fake:
        assert OllamaRouter("m", fake.base_url, timeout_s=0.2).choose("질문", MONOPOLE) is None


def test_the_default_timeout_is_15_seconds_and_reaches_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeouts = record_timeouts(monkeypatch)

    assert OllamaRouter("m", "http://127.0.0.1:11434").choose("질문", MONOPOLE) is None
    assert timeouts == [15.0]


def test_no_router_never_links() -> None:
    assert NoRouter().choose("선이 길면?", MONOPOLE) is None
