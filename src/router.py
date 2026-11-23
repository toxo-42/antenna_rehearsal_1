"""Link a student's question to one verified guide sentence. The model only picks a number;
it never writes the text the student sees."""

import re
from typing import Protocol

from src.guides import GUIDES, guide_for
from src.models import AntennaKind
from src.ollama import GenerateRequest, OllamaError, generate

ROUTE_OPTIONS = {"num_ctx": 4096, "num_predict": 6, "temperature": 0}
ROUTE_TIMEOUT_S = 15.0
GUIDE_KEYS: tuple[str, ...] = tuple(GUIDES)
MAX_DIGITS = 2

# Topics for picking a guide by hand when no model links the question.
TOPICS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("측정과 교정", ("positive_s11", "uncalibrated", "out_of_range", "band_edge", "no_resonance")),
    (
        "연결과 납땜",
        ("feed_short", "feed_open", "feed_fault", "lossy", "missing_fundamental", "feed_lead"),
    ),
    (
        "길이와 공진",
        (
            "length_far",
            "too_short",
            "too_long",
            "third_mode",
            "weak_fundamental",
            "other_resonance",
        ),
    ),
    ("정합과 케이블", ("r_low", "r_high", "reactance", "match_unknown", "common_mode")),
    ("대역폭과 완성", ("narrow", "good")),
)

PROMPT_HEAD = (
    "아래 설명 목록에서 학생 질문과 가장 관련 있는 설명 번호 하나만 고르세요. "
    "관련 있는 설명이 없으면 0. 숫자 하나만 답하세요."
)


class QuestionRouter(Protocol):
    def choose(self, question: str, kind: AntennaKind) -> int | None:
        """A guide number 1..24, 0 for "no related guide", or None when linking failed."""
        ...


class NoRouter:
    def choose(self, question: str, kind: AntennaKind) -> int | None:
        return None


class OllamaRouter:
    def __init__(self, model: str, base_url: str, timeout_s: float = ROUTE_TIMEOUT_S) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout_s = timeout_s

    def choose(self, question: str, kind: AntennaKind) -> int | None:
        prompt = build_route_prompt(question, kind)
        request = GenerateRequest(self.model, prompt, ROUTE_OPTIONS, self.timeout_s)
        try:
            return parse_choice(generate(self.base_url, request))
        except OllamaError:
            return None


def build_route_prompt(question: str, kind: AntennaKind) -> str:
    guides = [f"{n}. {guide_for(key, kind)}" for n, key in enumerate(GUIDE_KEYS, start=1)]
    return "\n".join(
        [PROMPT_HEAD, "", "설명 목록:", *guides, "", f"학생 질문: {question}", "번호:"]
    )


def parse_choice(answer: str) -> int | None:
    """The number when the answer holds exactly one 1-2 digit number in 0..24, else None."""
    found = re.findall(r"-?\d+", answer)  # keep a minus sign so "-1" is not read as 1
    if len(found) != 1 or not found[0].isdigit() or len(found[0]) > MAX_DIGITS:
        return None
    number = int(found[0])
    return number if number <= len(GUIDE_KEYS) else None


def key_for(number: int) -> str | None:
    """The guide key for a chosen number; None for 0."""
    return GUIDE_KEYS[number - 1] if number else None
