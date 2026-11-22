"""The change note grammar. Same lists as the select boxes in web/src/changeNote.ts."""

NO_CHANGE = "없음"
PARTS = (NO_CHANGE, "도체", "접지판", "케이블", "교정", "납땜")
ACTIONS = (NO_CHANGE, "줄임", "늘림", "변경")
AMOUNTS = (NO_CHANGE, "0.5", "1", "2", "3", "5", "10", "20", "50")
UNITS = ("mm", "cm", "%")


def is_structured(note: str) -> bool:
    """Whether `note` is "part [action] [amount unit]" as the select boxes build it, one space
    apart. Anything else (free text from the API) is not repeated in generated sentences."""
    words = note.split(" ")
    if words[0] not in PARTS[1:]:
        return False
    rest = words[1:]
    if rest and rest[0] in ACTIONS[1:]:
        rest = rest[1:]
    return rest == [] or (len(rest) == 2 and rest[0] in AMOUNTS[1:] and rest[1] in UNITS)
