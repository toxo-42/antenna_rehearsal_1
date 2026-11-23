"""Direction check holes: verb forms, checked sections, and negations far from the verb."""

import pytest

from scripts import eval_explain
from src import explain_check
from src.explain_check import review
from src.models import CalMode
from tests.test_explain_check import (
    ANTENNA,
    BARE_LENGTHEN_CARD,
    GOOD_CARD,
    LENGTHEN_CARD,
    SHORTEN_CARD,
    text,
)

RULE = "1. 안테나를 늘리면 공진 주파수가 낮아지고 줄이면 높아집니다."
LENGTHEN_TODO = "1. 도체를 약 11 % 늘리세요."


def status(written: str, card: object = LENGTHEN_CARD) -> str:
    return review(written, card, ANTENNA).status  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "todo",
    [
        "1. 안테나 길이를 줄여 보세요.",
        "1. 도체를 2 cm 잘라 주세요.",
        "1. 도체를 더 짧게 만드세요.",
        "1. 도체를 줄인 뒤 다시 잽니다.",
        "1. 도체를 자른 뒤 다시 잽니다.",
    ],
)
def test_a_lengthen_card_rejects_every_form_of_shortening(todo: str) -> None:
    assert status(text(todo=todo), BARE_LENGTHEN_CARD) == "rejected"
    assert status(text(todo=todo), SHORTEN_CARD) == "ok"


@pytest.mark.parametrize(
    "todo",
    [
        "1. 도체를 늘려 주세요.",
        "1. 도체를 더 길게 만드세요.",
        "1. 도체를 늘린 뒤 다시 잽니다.",
        "1. 도체에 선을 덧대 주세요.",
    ],
)
def test_a_shorten_card_rejects_every_form_of_lengthening(todo: str) -> None:
    assert status(text(todo=todo), SHORTEN_CARD) == "rejected"
    assert status(text(todo=todo), BARE_LENGTHEN_CARD) == "ok"


def test_the_first_and_the_last_section_are_checked_too() -> None:
    good = text(todo=LENGTHEN_TODO)
    first = good.replace("공진은 있지만 목표에 맞지 않습니다.", "도체를 자르세요.")
    last = good.replace("1. 다시 재서 공진이", "1. 도체를 자르세요. 다시 재서 공진이")

    assert "도체를 자르세요." in first and "도체를 자르세요." in last
    assert review(first, LENGTHEN_CARD, ANTENNA).reasons == ("방향: 도체를 자르세요.",)
    assert review(last, LENGTHEN_CARD, ANTENNA).reasons == ("방향: 도체를 자르세요.",)


def test_the_two_explaining_sections_stay_unchecked() -> None:
    state = text().replace("## 지금 상태\n", f"## 지금 상태\n{RULE}\n")

    assert status(text(why=RULE), SHORTEN_CARD) == "ok"
    assert status(text(why=RULE, todo=LENGTHEN_TODO), LENGTHEN_CARD) == "ok"
    assert status(state, SHORTEN_CARD) == "ok"


def test_the_checked_sections_are_one_constant() -> None:
    assert explain_check.CHECKED_SECTIONS == (
        explain_check.FIRST,
        "지금 해 볼 것",
        "다시 재서 확인할 것",
    )


@pytest.mark.parametrize(
    "todo",
    [
        "1. 접지판은 건드리지 말고 도체를 자르세요.",
        "1. 늘리는 대신 도체를 자르세요.",
        "1. 손은 대지 마세요, 그리고 도체를 자르세요.",
        "1. 도체를 자르세요, 다만 접지판은 건드리지 마세요.",
    ],
)
def test_a_negation_away_from_the_verb_does_not_excuse_it(todo: str) -> None:
    assert status(text(todo=todo)) == "rejected"
    assert status(text(todo=todo), GOOD_CARD) == "rejected"


@pytest.mark.parametrize(
    "todo",
    [
        "1. 도체를 자르지 마세요.",
        "1. 도체를 자르지 말고 덧붙여서 확인합니다.",
        "1. 도체를 줄이지 않고 덧붙입니다.",
        "1. 길이를 자르는 행동은 하지 마세요.",
    ],
)
def test_a_negation_right_after_the_verb_excuses_it(todo: str) -> None:
    assert status(text(todo=todo)) == "ok"


def test_one_excused_and_one_plain_occurrence_is_still_wrong() -> None:
    assert status(text(todo="1. 도체를 자르지 말고, 아니 그냥 도체를 자르세요.")) == "rejected"


def test_the_window_is_six_characters_after_the_word() -> None:
    assert status(text(todo="1. 도체를 자르123456마세요.")) == "ok"
    assert status(text(todo="1. 도체를 자르1234567마세요.")) == "rejected"


def test_the_eval_script_uses_ten_different_cards() -> None:
    names = [(name, target) for name, _, target, _ in eval_explain.MEASURED]

    assert len(set(names)) == len(names) == 6
    assert ("monopole_10cm_weak.csv", 750.0) in names
    assert len({name for name, _ in names}) == 6
    assert len(eval_explain.MEASURED) + len(eval_explain.SYNTHETIC) == 10
    modes = {name: mode for name, _, _, mode in eval_explain.MEASURED}
    assert modes.pop("saa2_patch_2450.csv") is CalMode.UNKNOWN
    assert set(modes.values()) == {CalMode.VNA}
