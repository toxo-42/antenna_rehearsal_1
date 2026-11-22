"""Local-model help on a stored measurement: explain its card, link a question to a guide.

Neither changes the card. Generated text is never stored.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src import service
from src.explain import Explainer, NoExplainer, OllamaExplainer
from src.guides import guide_for
from src.models import Antenna, AntennaKind, Card, CardStage, Diagnosis
from src.ollama import DEFAULT_BASE_URL, DEFAULT_MODEL
from src.router import TOPICS, NoRouter, OllamaRouter, QuestionRouter, key_for

MAX_QUESTION_CHARS = 200
Row = dict[str, Any]


@dataclass(frozen=True)
class LlmParts:
    explainer: Explainer
    router: QuestionRouter


def parts_from_env(env: Mapping[str, str]) -> LlmParts:
    """OLLAMA_MODEL (unset: the contest default, empty: both off) and OLLAMA_EXPLAIN=off."""
    model = env.get("OLLAMA_MODEL", DEFAULT_MODEL).strip()
    if not model:
        return LlmParts(NoExplainer(), NoRouter())
    router = OllamaRouter(model, DEFAULT_BASE_URL)
    if env.get("OLLAMA_EXPLAIN", "").strip().lower() == "off":
        return LlmParts(NoExplainer(), router)
    return LlmParts(OllamaExplainer(model, DEFAULT_BASE_URL), router)


def health_flags(parts: LlmParts) -> dict[str, bool]:
    """`ollama`: questions are linked by a model. `explain`: the explain button is shown."""
    return {
        "ollama": not isinstance(parts.router, NoRouter),
        "explain": not isinstance(parts.explainer, NoExplainer),
    }


def card_from_dict(data: Mapping[str, Any]) -> Card:
    return Card(
        stage=CardStage(data["stage"]),
        headline=data["headline"],
        status=tuple(data["status"]),
        diagnoses=tuple(Diagnosis(**item) for item in data["diagnoses"]),
    )


def explain_measurement(db_path: Path, measurement_id: int, explainer: Explainer) -> Row:
    measurement = service.get_measurement(db_path, measurement_id)
    stored = measurement["antenna"]
    antenna = Antenna(stored["name"], AntennaKind(stored["kind"]), stored["target_mhz"])
    result = explainer.explain(card_from_dict(measurement["card"]), antenna)
    row = {**asdict(result), "warnings": list(result.warnings)}
    del row["rejections"]  # quotes a dropped text, which the screen never shows
    return row


def ask_measurement(
    db_path: Path, measurement_id: int, question: str, router: QuestionRouter
) -> Row:
    """Link `question` to one guide. The model's answer is used only as a number."""
    measurement = service.get_measurement(db_path, measurement_id)
    question = _checked_question(question)
    kind = AntennaKind(measurement["antenna"]["kind"])
    number = router.choose(question, kind)
    if number is None:
        return _no_link("failed")
    key = key_for(number)
    if key is None:
        return _no_link("none")
    return {"status": "matched", **_guide_item(key, kind, _card_actions(measurement))}


def guide_choices(db_path: Path, measurement_id: int) -> list[Row]:
    """Every guide grouped by topic, for picking by hand when a question was not linked."""
    measurement = service.get_measurement(db_path, measurement_id)
    kind = AntennaKind(measurement["antenna"]["kind"])
    actions = _card_actions(measurement)
    return [
        {"topic": topic, "items": [_guide_item(key, kind, actions) for key in keys]}
        for topic, keys in TOPICS
    ]


def _checked_question(question: str) -> str:
    question = question.strip()
    if not question:
        raise service.InputError("질문을 입력해 주세요.")
    if len(question) > MAX_QUESTION_CHARS:
        raise service.InputError(f"질문은 {MAX_QUESTION_CHARS}자 이하로 써 주세요.")
    return question


def _card_actions(measurement: Row) -> dict[str, str]:
    return {item["key"]: item["action"] for item in measurement["card"]["diagnoses"]}


def _guide_item(key: str, kind: AntennaKind, actions: dict[str, str]) -> Row:
    """`action` is the card's own value, and only when this key is on the card."""
    return {
        "key": key,
        "guide": guide_for(key, kind),
        "in_card": key in actions,
        "action": actions.get(key),
    }


def _no_link(status: str) -> Row:
    return {"status": status, "key": None, "guide": None, "in_card": False, "action": None}
