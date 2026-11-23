"""The change note grammar. Same lists and amount pattern as web/src/changeNote.ts."""

import re

NO_CHANGE = "없음"
PARTS = (NO_CHANGE, "도체", "접지판", "케이블", "교정", "납땜")
ACTIONS = (NO_CHANGE, "줄임", "늘림", "변경")
UNITS = ("mm", "cm", "%")
# The amount is typed by the student: a plain number, up to 4 digits and 2 decimals, above zero.
AMOUNT_PATTERN = re.compile(r"^(0|[1-9]\d{0,3})(\.\d{1,2})?$")


def is_amount(text: str) -> bool:
    """Whether `text` is a plain positive number as the amount box accepts it."""
    return AMOUNT_PATTERN.fullmatch(text) is not None and float(text) > 0


def is_structured(note: str) -> bool:
    """Whether `note` is "part [action] [amount unit]" as the measure screen builds it, one space
    apart. Anything else (free text from the API) is not repeated in generated sentences."""
    words = note.split(" ")
    if words[0] not in PARTS[1:]:
        return False
    rest = words[1:]
    if rest and rest[0] in ACTIONS[1:]:
        rest = rest[1:]
    return rest == [] or (len(rest) == 2 and is_amount(rest[0]) and rest[1] in UNITS)
