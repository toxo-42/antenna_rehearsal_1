"""Pure checks on a generated explanation against its card: format, length direction, numbers.

Only format and direction can reject a text. Numbers missing from the card become warnings.
"""

import math
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal

from src.models import Antenna, AntennaKind, Card

KIND_NAME = {AntennaKind.MONOPOLE: "모노폴", AntennaKind.PATCH: "패치"}
HEADING = "## "
HEADINGS = ("지금 상태", "왜 이렇게 나왔나", "지금 해 볼 것", "다시 재서 확인할 것")
TODO = "지금 해 볼 것"
LENGTHEN = "늘리"
SHORTEN = "줄이"
CUT = "자르"
ADD = "덧붙"
LENGTH_WORDS = ("도체", "길이", "안테나")
NEGATIONS = (
    "마세요", "하지 마", "하지 않", "말고", "않도록", "안 됩니다", "금지", "금물", "대신", "필요 없",
)  # fmt: skip

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_LIST_MARK = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class Review:
    status: str  # "ok" or "rejected"
    warnings: tuple[str, ...]
    reasons: tuple[str, ...] = ()  # why it was rejected: "형식: …" or "방향: <sentence>"


def review(text: str, card: Card, antenna: Antenna) -> Review:
    """Reject on format or direction; otherwise keep the text and list unknown numbers.
    `antenna` is the card's first line in the prompt, so its target counts as a card number."""
    if not format_ok(text):
        return Review("rejected", (), (f"형식: 제목 {headings(text)}",))
    wrong = wrong_sentences(text, card)
    if wrong:
        return Review("rejected", (), tuple(f"방향: {sentence}" for sentence in wrong))
    return Review("ok", tuple(unknown_numbers(text, card, antenna)))


def headings(text: str) -> list[str]:
    return [line[len(HEADING) :].strip() for line in text.splitlines() if line.startswith(HEADING)]


def format_ok(text: str) -> bool:
    """Exactly five `## ` headings; the last four are the fixed ones in order."""
    found = headings(text)
    return len(found) == 1 + len(HEADINGS) and tuple(found[1:]) == HEADINGS


def section(text: str, title: str) -> str:
    """The lines under one of the four fixed headings, found by its position (the free first
    heading may use the same words). Call it only on a text that passed `format_ok`."""
    position = 1 + HEADINGS.index(title)
    lines: list[str] = []
    count = -1
    for line in text.splitlines():
        if line.startswith(HEADING):
            count += 1
        elif count == position:
            lines.append(line)
    return "\n".join(lines)


def forbidden_words(card: Card) -> tuple[str, ...]:
    """Words the "지금 해 볼 것" section may not use, from the directions in the card's actions.
    A word the actions already contain is allowed: copying "자르지 말고 덧붙여서" is faithful."""
    actions = " ".join(d.action for d in card.diagnoses)
    return tuple(word for word in _direction_words(actions) if word not in actions)


def _direction_words(actions: str) -> tuple[str, ...]:
    longer, shorter = LENGTHEN in actions, SHORTEN in actions
    if longer and shorter:
        return ()
    if longer:
        return (SHORTEN, CUT)
    if shorter:
        return (LENGTHEN, ADD)
    return (SHORTEN, LENGTHEN, CUT, ADD)


def sentences(text: str) -> list[str]:
    """Lines, each split after `.`, `!` or `?` followed by a space. Empty pieces are dropped."""
    pieces = (piece.strip() for line in text.splitlines() for piece in _SENTENCE_END.split(line))
    return [piece for piece in pieces if piece]


def _breaks_direction(sentence: str, forbidden: tuple[str, ...]) -> bool:
    return (
        any(word in sentence for word in forbidden)
        and any(word in sentence for word in LENGTH_WORDS)
        and not any(word in sentence for word in NEGATIONS)
    )


def wrong_sentences(text: str, card: Card) -> list[str]:
    """Sentences of "지금 해 볼 것" with a forbidden word, a word naming the length, and no
    negation. A forbidden word alone is not enough: "접지판을 늘리거나" is not about length."""
    forbidden = forbidden_words(card)
    return [s for s in sentences(section(text, TODO)) if _breaks_direction(s, forbidden)]


def direction_ok(text: str, card: Card) -> bool:
    return not wrong_sentences(text, card)


def numbers_in(text: str) -> list[str]:
    """Numbers as written, without list marks at line starts and with thousands commas removed."""
    cleaned = _THOUSANDS.sub("", _LIST_MARK.sub("", text))
    return _NUMBER.findall(cleaned)


def antenna_line(antenna: Antenna) -> str:
    """The first line of the card as the model sees it: antenna kind and target frequency."""
    return f"안테나: {KIND_NAME[antenna.kind]}, 목표 {antenna.target_mhz:g} MHz"


def card_text(card: Card, antenna: Antenna) -> str:
    parts = [antenna_line(antenna), card.headline, *card.status]
    for d in card.diagnoses:
        parts += [d.title, d.evidence, d.action, d.guide]
    return "\n".join(parts)


def allowed_numbers(card: Card, antenna: Antenna) -> set[Decimal]:
    """Card numbers (the target included), their whole-number round/ceil/floor, their one-decimal
    rounding, and 0."""
    allowed = {Decimal(0)}
    for written in _NUMBER.findall(card_text(card, antenna)):
        value = Decimal(written)
        exact = Context(prec=len(written) + 2)  # the default 28 digits fail on long values
        allowed |= {value, Decimal(math.floor(value)), Decimal(math.ceil(value))}
        allowed.add(value.quantize(Decimal(1), rounding=ROUND_HALF_UP, context=exact))
        allowed.add(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP, context=exact))
    return allowed


def unknown_numbers(text: str, card: Card, antenna: Antenna) -> list[str]:
    """Numbers in `text` that the card does not have, each listed once in order of appearance."""
    allowed = allowed_numbers(card, antenna)
    unknown: list[str] = []
    for written in numbers_in(text):
        if Decimal(written) not in allowed and written not in unknown:
            unknown.append(written)
    return unknown
