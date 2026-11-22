"""OllamaExplainer against a fake HTTP server, and the prompt built from a card."""

import pytest

from src.explain import EXPLAIN_OPTIONS, NoExplainer, OllamaExplainer, build_prompt
from src.models import Card, CardStage, Diagnosis
from tests.fake_ollama import closed_port_url, fake_ollama, record_timeouts

CARD = Card(
    stage=CardStage.OFFTARGET,
    headline="공진은 있지만 목표 주파수에 맞지 않습니다",
    status=("공진 381.25 MHz (목표 -51.75 MHz, -11.95 %)", "S11 -25.21 dB (깊이 25.06 dB)"),
    diagnoses=(
        Diagnosis("too_long", "안테나 도체가 김", "공진 381.25 MHz, 목표 433 MHz",
                  "안테나 도체를 약 12 % 줄이는 것이 초기 추정", "도체가 길면 공진 주파수가 낮아진다."),
        Diagnosis("feed_lead", "급전부의 노출된 선이 김", "공진 381.25 MHz, 목표 433 MHz",
                  "노출된 급전선을 짧게", "납땜 덩어리가 크면 공진 주파수가 낮아진다."),
    ),
)  # fmt: skip

GOOD_TEXT = (
    "## 한 줄 결론\n목표에 맞지 않습니다.\n## 지금 상태\n1. 공진은 381.25 MHz입니다.\n"
    "## 왜 이렇게 나왔나\n1. 도체가 깁니다.\n## 지금 해 볼 것\n1. 도체를 약 12 % 줄이세요.\n"
    "## 다시 재서 확인할 것\n1. 다시 잽니다.\n"
)


def test_the_prompt_ends_with_the_card_in_order() -> None:
    prompt = build_prompt(CARD)

    assert prompt.startswith("당신은 안테나 실습 조교입니다.")
    assert "## 다시 재서 확인할 것\n\n프로그램 판정:\n" in prompt
    card_part = prompt.split("프로그램 판정:\n", 1)[1]
    assert card_part.splitlines()[:3] == [CARD.headline, *CARD.status]
    assert (
        "1. 안테나 도체가 김 / 근거: 공진 381.25 MHz, 목표 433 MHz / "
        "해 볼 것: 안테나 도체를 약 12 % 줄이는 것이 초기 추정 / "
        "설명: 도체가 길면 공진 주파수가 낮아진다."
    ) in card_part
    assert card_part.index("1. 안테나 도체가 김") < card_part.index("2. 급전부의 노출된 선이 김")


def test_a_good_answer_is_ok_and_the_request_follows_the_spec() -> None:
    with fake_ollama(GOOD_TEXT) as fake:
        result = OllamaExplainer("qwen3.5:4b", fake.base_url).explain(CARD)

    assert (result.status, result.text, result.warnings) == ("ok", GOOD_TEXT.strip(), ())
    assert result.model == "qwen3.5:4b"
    assert result.seconds is not None and result.seconds >= 0
    assert fake.paths == ["/api/generate"]
    body = fake.requests[0]
    assert body["model"] == "qwen3.5:4b"
    assert body["prompt"] == build_prompt(CARD)
    assert (body["stream"], body["think"], body["keep_alive"]) == (False, False, "10m")
    assert body["options"] == EXPLAIN_OPTIONS
    assert EXPLAIN_OPTIONS == {"num_ctx": 4096, "num_predict": 700, "temperature": 0.2,
                               "repeat_penalty": 1.1}  # fmt: skip
    assert "format" not in body


def test_a_missing_heading_is_rejected_and_the_text_dropped() -> None:
    with fake_ollama(GOOD_TEXT.replace("## 지금 상태\n", "")) as fake:
        result = OllamaExplainer("m", fake.base_url).explain(CARD)

    assert (result.status, result.text) == ("rejected", None)


def test_the_opposite_direction_is_rejected() -> None:
    with fake_ollama(GOOD_TEXT.replace("줄이세요", "늘리세요")) as fake:
        result = OllamaExplainer("m", fake.base_url).explain(CARD)

    assert (result.status, result.text) == ("rejected", None)


def test_unknown_numbers_are_warned_but_kept() -> None:
    answer = GOOD_TEXT.replace("12 % 줄이세요", "길이 50cm → 44cm로 줄이세요")
    with fake_ollama(answer) as fake:
        result = OllamaExplainer("m", fake.base_url).explain(CARD)

    assert result.status == "ok"
    assert result.warnings == ("50", "44")


def test_a_body_cut_short_fails() -> None:
    with fake_ollama(GOOD_TEXT, extra_length=50) as fake:
        result = OllamaExplainer("m", fake.base_url).explain(CARD)

    assert (result.status, result.text) == ("failed", None)


def test_a_refused_connection_fails() -> None:
    result = OllamaExplainer("m", closed_port_url()).explain(CARD)

    assert (result.status, result.text, result.warnings) == ("failed", None, ())


def test_a_timeout_fails() -> None:
    with fake_ollama(GOOD_TEXT, delay_s=1.0) as fake:
        result = OllamaExplainer("m", fake.base_url, timeout_s=0.2).explain(CARD)

    assert (result.status, result.text) == ("failed", None)


def test_the_default_timeout_is_120_seconds_and_reaches_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeouts = record_timeouts(monkeypatch)

    result = OllamaExplainer("m", "http://127.0.0.1:11434").explain(CARD)

    assert result.status == "failed"
    assert timeouts == [120.0]


def test_an_http_error_or_a_broken_body_fails() -> None:
    with fake_ollama(status=501, raw_body=b'{"error": "not implemented"}') as fake:
        assert OllamaExplainer("m", fake.base_url).explain(CARD).status == "failed"
    with fake_ollama(raw_body=b"not json") as fake:
        assert OllamaExplainer("m", fake.base_url).explain(CARD).status == "failed"
    with fake_ollama(raw_body=b'{"done": true}') as fake:
        assert OllamaExplainer("m", fake.base_url).explain(CARD).status == "failed"


def test_no_explainer_is_off() -> None:
    result = NoExplainer().explain(CARD)

    assert (result.status, result.text, result.warnings, result.model) == ("off", None, (), None)
