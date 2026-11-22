"""Pure checks on a generated explanation against its card: format, length direction, numbers.

Only format and direction can reject a text. Numbers missing from the card become warnings.
"""

import math
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal

from src.models import Card

HEADING = "## "
HEADINGS = ("지금 상태", "왜 이렇게 나왔나", "지금 해 볼 것", "다시 재서 확인할 것")
TODO = "지금 해 볼 것"
LENGTHEN = "늘리"
SHORTEN = "줄이"
CUT = "자르"
ADD = "덧붙"

_LIST_MARK = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class Review:
    status: str  # "ok" or "rejected"
    warnings: tuple[str, ...]


def review(text: str, card: Card) -> Review:
    """Reject on format or direction; otherwise keep the text and list unknown numbers."""
    if not (format_ok(text) and direction_ok(text, card)):
        return Review("rejected", ())
    return Review("ok", tuple(unknown_numbers(text, card)))


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
    """Words the "지금 해 볼 것" section may not use, from the directions in the card's actions."""
    actions = " ".join(d.action for d in card.diagnoses)
    longer, shorter = LENGTHEN in actions, SHORTEN in actions
    if longer and shorter:
        return ()
    if longer:
        return (SHORTEN, CUT)
    if shorter:
        return (LENGTHEN, ADD)
    return (SHORTEN, LENGTHEN, CUT, ADD)


def direction_ok(text: str, card: Card) -> bool:
    todo = section(text, TODO)
    return not any(word in todo for word in forbidden_words(card))


def numbers_in(text: str) -> list[str]:
    """Numbers as written, without list marks at line starts and with thousands commas removed."""
    cleaned = _THOUSANDS.sub("", _LIST_MARK.sub("", text))
    return _NUMBER.findall(cleaned)


def card_text(card: Card) -> str:
    parts = [card.headline, *card.status]
    for d in card.diagnoses:
        parts += [d.title, d.evidence, d.action, d.guide]
    return "\n".join(parts)


def allowed_numbers(card: Card) -> set[Decimal]:
    """Card numbers, their whole-number round/ceil/floor, their one-decimal rounding, and 0."""
    allowed = {Decimal(0)}
    for written in _NUMBER.findall(card_text(card)):
        value = Decimal(written)
        exact = Context(prec=len(written) + 2)  # the default 28 digits fail on long values
        allowed |= {value, Decimal(math.floor(value)), Decimal(math.ceil(value))}
        allowed.add(value.quantize(Decimal(1), rounding=ROUND_HALF_UP, context=exact))
        allowed.add(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP, context=exact))
    return allowed


def unknown_numbers(text: str, card: Card) -> list[str]:
    """Numbers in `text` that the card does not have, each listed once in order of appearance."""
    allowed = allowed_numbers(card)
    unknown: list[str] = []
    for written in numbers_in(text):
        if Decimal(written) not in allowed and written not in unknown:
            unknown.append(written)
    return unknown
