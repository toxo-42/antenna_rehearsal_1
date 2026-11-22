"""Checks on a generated explanation: format, length direction, numbers. Strings only, no model."""

import pytest

from src.explain_check import format_ok, review, section, unknown_numbers, wrong_sentences
from src.models import Antenna, AntennaKind, CalMode, Card, CardStage, Diagnosis
from src.synthetic import make_sample
from src.verdict import build_card

ANTENNA = Antenna("a", AntennaKind.MONOPOLE, 433.0)
SHORTEN_ACTION = (
    "안테나 도체를 약 12 % 줄이는 것이 초기 추정. 한 번에 절반씩, 자르기 전에 다시 측정"
)
LENGTHEN_ACTION = (
    "안테나 도체를 약 11 % 늘리는 것이 초기 추정. 한 번에 절반씩, 자르지 말고 덧붙여서 확인"
)


def card_with(*actions: str, stage: CardStage = CardStage.OFFTARGET) -> Card:
    diagnoses = tuple(
        Diagnosis(
            key=f"k{i}",
            title="제목",
            evidence="공진 381.25 MHz, 목표 433 MHz",
            action=action,
            guide="설명",
        )
        for i, action in enumerate(actions)
    )
    status = ("공진 381.25 MHz (목표 -51.75 MHz, -11.95 %)", "다른 공진 1833.9 MHz")
    return Card(stage=stage, headline="공진은 있지만 목표 주파수에 맞지 않습니다",
                status=status, diagnoses=diagnoses)  # fmt: skip


SHORTEN_CARD = card_with(SHORTEN_ACTION, "노출된 급전선을 짧게")
LENGTHEN_CARD = card_with(LENGTHEN_ACTION)
BARE_LENGTHEN_CARD = card_with("안테나 도체를 약 11 % 늘리기")
GOOD_CARD = card_with("손·케이블 위치를 바꿔도 유지되는지 확인하고 저장", stage=CardStage.GOOD)
BOTH_CARD = card_with(SHORTEN_ACTION, LENGTHEN_ACTION)


def text(
    todo: str = "1. 도체를 약 12 % 줄이세요. 한 번에 절반씩 합니다.\n2. 노출된 급전선을 짧게 합니다.",
    first: str = "한 줄 결론",
    why: str = "1. 도체가 깁니다. 늘리면 낮아지고 줄이면 높아집니다.",
) -> str:
    return (
        f"## {first}\n공진은 있지만 목표에 맞지 않습니다.\n"
        "## 지금 상태\n1. 공진(가장 잘 울리는 주파수)은 381.25 MHz, 목표는 433 MHz입니다.\n"
        f"## 왜 이렇게 나왔나\n{why}\n"
        f"## 지금 해 볼 것\n{todo}\n"
        "## 다시 재서 확인할 것\n1. 다시 재서 공진이 목표 쪽으로 올라갔는지 봅니다.\n"
    )


def test_a_faithful_text_passes_without_warnings() -> None:
    result = review(text(), SHORTEN_CARD, ANTENNA)

    assert result.status == "ok"
    assert result.warnings == ()


def test_a_missing_heading_is_rejected() -> None:
    broken = text().replace("## 다시 재서 확인할 것\n", "")

    assert not format_ok(broken)
    assert review(broken, SHORTEN_CARD, ANTENNA).status == "rejected"


def test_a_different_first_heading_passes() -> None:
    assert review(text(first="안테나 도체가 김"), SHORTEN_CARD, ANTENNA).status == "ok"


def test_an_extra_heading_or_a_wrong_order_is_rejected() -> None:
    extra = text() + "## 덧붙임\n없음\n"
    swapped = (
        text().replace("## 지금 상태", "## 임시").replace("## 왜 이렇게 나왔나", "## 지금 상태")
    )

    assert not format_ok(extra)
    assert not format_ok(swapped)
    assert not format_ok("제목 없는 글")


def test_section_returns_only_the_lines_under_one_heading() -> None:
    todo = section(text(), "지금 해 볼 것")

    assert "12 % 줄이세요" in todo
    assert "다시 재서" not in todo
    assert "늘리면" not in todo


def test_the_opposite_direction_in_the_todo_section_is_rejected() -> None:
    wrong = text(todo="1. 도체를 약 12 % 늘리세요.")

    assert review(wrong, SHORTEN_CARD, ANTENNA).status == "rejected"


def test_the_rule_sentence_in_another_section_passes() -> None:
    why = "1. 안테나를 늘리면 공진이 낮아지고 줄이면 높아집니다. 자르거나 덧붙여 맞춥니다."

    assert review(text(why=why), SHORTEN_CARD, ANTENNA).status == "ok"


def test_a_shorten_card_rejects_adding_wire() -> None:
    todo = "1. 도체에 선을 덧붙이세요."

    assert review(text(todo=todo), SHORTEN_CARD, ANTENNA).status == "rejected"


def test_a_shorten_card_rejects_lengthening_the_antenna() -> None:
    todo = "1. 안테나 길이를 늘리세요."

    assert review(text(todo=todo), SHORTEN_CARD, ANTENNA).status == "rejected"


def test_a_good_card_rejects_cutting_the_conductor_but_not_a_warning_against_it() -> None:
    def status(todo: str) -> str:
        return review(text(todo=todo), GOOD_CARD, ANTENNA).status

    assert status("1. 도체를 자르세요.") == "rejected"
    assert status("1. 길이를 자르는 행동은 하지 마세요.") == "ok"


def test_a_forbidden_word_that_is_not_about_the_length_passes() -> None:
    ground = "1. 접지판 크기를 늘리거나 위치를 바꿔 봅니다."
    resonance = "1. 공진을 줄이기 위해 급전부를 확인합니다."

    assert review(text(todo=ground), SHORTEN_CARD, ANTENNA).status == "ok"
    assert review(text(todo=resonance), BARE_LENGTHEN_CARD, ANTENNA).status == "ok"


@pytest.mark.parametrize(
    "negation",
    [
        "마세요",
        "하지 마",
        "하지 않",
        "말고",
        "않도록",
        "안 됩니다",
        "금지",
        "금물",
        "대신",
        "필요 없",
    ],
)
def test_each_negation_keeps_a_length_sentence(negation: str) -> None:
    todo = f"1. 도체 길이를 자르는 일: {negation}."

    assert review(text(todo=todo), GOOD_CARD, ANTENNA).status == "ok"


def test_the_three_conditions_must_meet_in_one_sentence() -> None:
    apart = "1. 급전선을 자르세요. 안테나는 그대로 둡니다."
    negation_elsewhere = "1. 도체를 자르세요. 손은 대지 마세요."
    next_line = "1. 도체를 자르세요\n2. 케이블은 만지지 마세요"

    assert review(text(todo=apart), GOOD_CARD, ANTENNA).status == "ok"
    assert review(text(todo=negation_elsewhere), GOOD_CARD, ANTENNA).status == "rejected"
    assert review(text(todo=next_line), GOOD_CARD, ANTENNA).status == "rejected"


def test_wrong_sentences_names_each_offending_sentence() -> None:
    todo = "1. 손 위치를 바꿉니다. 도체를 자르세요.\n2. 안테나 길이를 늘리세요."

    assert wrong_sentences(text(todo=todo), GOOD_CARD) == [
        "도체를 자르세요.",
        "안테나 길이를 늘리세요.",
    ]


def test_a_rejection_gives_its_reason() -> None:
    direction = review(text(todo="1. 도체를 자르세요."), GOOD_CARD, ANTENNA)
    broken = review(text().replace("## 지금 상태\n", ""), GOOD_CARD, ANTENNA)

    assert direction.reasons == ("방향: 도체를 자르세요.",)
    assert len(broken.reasons) == 1 and broken.reasons[0].startswith("형식: ")
    assert review(text(), SHORTEN_CARD, ANTENNA).reasons == ()


def test_a_lengthen_card_rejects_shortening_or_cutting() -> None:
    def status(todo: str) -> str:
        return review(text(todo=todo), BARE_LENGTHEN_CARD, ANTENNA).status

    assert status("1. 도체를 약 11 % 늘리세요.") == "ok"
    assert status("1. 도체를 줄이세요.") == "rejected"
    assert status("1. 도체를 자르세요.") == "rejected"


def test_words_already_in_the_card_actions_are_not_forbidden() -> None:
    copied = "1. 도체를 약 11 % 늘리세요. 자르지 말고 덧붙여서 확인합니다."

    assert review(text(todo=copied), LENGTHEN_CARD, ANTENNA).status == "ok"
    assert review(text(todo="1. 도체를 줄이세요."), LENGTHEN_CARD, ANTENNA).status == "rejected"


@pytest.mark.parametrize("name", ["offtarget_high", "far_low"])
def test_a_synthetic_card_with_its_actions_copied_passes(name: str) -> None:
    sample = make_sample(name)
    card = build_card(sample.sweep, sample.antenna, CalMode.VNA)
    todo = "\n".join(f"{n}. {d.action}" for n, d in enumerate(card.diagnoses, start=1))

    assert review(text(todo=todo), card, sample.antenna).status == "ok"


def test_the_lengthen_sample_copies_the_cut_word() -> None:
    sample = make_sample("offtarget_high")
    actions = [d.action for d in build_card(sample.sweep, sample.antenna, CalMode.VNA).diagnoses]

    assert any("늘리" in action and "자르" in action for action in actions)


def test_the_target_frequency_counts_as_a_card_number() -> None:
    target_1350 = Antenna("a", AntennaKind.MONOPOLE, 1350.0)

    assert unknown_numbers("목표 1350 MHz", GOOD_CARD, target_1350) == []
    assert unknown_numbers("목표 1350 MHz", GOOD_CARD, ANTENNA) == ["1350"]


def test_a_good_card_rejects_any_length_change() -> None:
    for verb in ("자르세요", "줄이세요", "늘리세요", "덧붙이세요"):
        assert review(text(todo=f"1. 도체를 {verb}."), GOOD_CARD, ANTENNA).status == "rejected", (
            verb
        )
    assert review(text(todo="1. 손 위치를 바꿔 봅니다."), GOOD_CARD, ANTENNA).status == "ok"


def test_a_first_heading_named_like_the_todo_heading_is_not_checked() -> None:
    first = "1. 도체를 늘리면 공진이 낮아집니다."
    written = text(first="지금 해 볼 것").replace("공진은 있지만 목표에 맞지 않습니다.", first)

    assert format_ok(written)
    assert "늘리면" not in section(written, "지금 해 볼 것")
    assert review(written, SHORTEN_CARD, ANTENNA).status == "ok"


def test_a_card_value_with_many_digits_is_read_without_error() -> None:
    huge = "1" + "0" * 30 + ".25"
    card = card_with(f"공진점 X +{huge} Ω")

    assert unknown_numbers(f"X는 {huge} 옴", card, ANTENNA) == []
    assert unknown_numbers("X는 7 옴", card, ANTENNA) == ["7"]


def test_a_card_with_both_directions_skips_the_direction_check() -> None:
    assert review(text(todo="1. 줄이거나 늘리세요."), BOTH_CARD, ANTENNA).status == "ok"


def test_numbers_missing_from_the_card_become_warnings() -> None:
    result = review(text(todo="1. 길이 50cm → 44cm로 줄이세요."), SHORTEN_CARD, ANTENNA)

    assert result.status == "ok"
    assert result.warnings == ("50", "44")


def test_rounded_card_numbers_and_zero_are_not_warnings() -> None:
    written = "공진 381, 381.3, 382 MHz, 다른 공진 1,834 MHz, 차이 -11.95 %, 0 dB"

    assert unknown_numbers(written, SHORTEN_CARD, ANTENNA) == []


def test_card_numbers_rounded_down_are_not_warnings() -> None:
    # 1833.9 and 51.75 round and ceil up, so only the floor rule allows 1833 and 51.
    assert unknown_numbers("다른 공진 1833 MHz, 차이 51 MHz", SHORTEN_CARD, ANTENNA) == []
    assert unknown_numbers("1832 MHz, 50 MHz", SHORTEN_CARD, ANTENNA) == ["1832", "50"]


def test_list_numbers_at_line_start_are_not_read() -> None:
    assert unknown_numbers("7. 첫째\n  8. 둘째", SHORTEN_CARD, ANTENNA) == []
    assert unknown_numbers("항목 7. 다음", SHORTEN_CARD, ANTENNA) == ["7"]


def test_a_number_near_but_not_a_rounding_of_a_card_value_is_a_warning() -> None:
    assert unknown_numbers("380 MHz, 381.4 MHz", SHORTEN_CARD, ANTENNA) == ["380", "381.4"]


def test_a_repeated_unknown_number_is_listed_once() -> None:
    assert unknown_numbers("50 cm, 그리고 다시 50 cm", SHORTEN_CARD, ANTENNA) == ["50"]
