"""The change note grammar shared with the select boxes in web/src/changeNote.ts."""

import re
from pathlib import Path

import pytest

from src import change_note

WEB_LISTS = Path(__file__).resolve().parent.parent / "web" / "src" / "changeNote.ts"


@pytest.mark.parametrize(
    "note",
    ["도체 줄임 5 mm", "접지판 늘림 0.5 cm", "케이블 변경", "교정", "납땜 변경 10 %", "도체 2 mm"],
)
def test_notes_built_from_the_select_boxes_are_recognized(note: str) -> None:
    assert change_note.is_structured(note)


@pytest.mark.parametrize(
    "note",
    [
        "",
        "케이블 때문에 개선됐다",
        "첫 측정",
        "없음",
        "도체 줄임 5",
        "도체 줄임 mm",
        "도체 줄임 7 mm",
        "도체  줄임 5 mm",
        "도체 줄임 5 mm 더",
        "줄임 도체",
    ],
)
def test_anything_else_is_not(note: str) -> None:
    assert not change_note.is_structured(note)


def ts_list(name: str) -> tuple[str, ...]:
    """The string items of `export const NAME = [...]` in changeNote.ts (NO_CHANGE included)."""
    text = WEB_LISTS.read_text(encoding="utf-8")
    body = re.search(rf"export const {name} = \[(.*?)\]", text, re.DOTALL)
    assert body is not None, name
    items = re.findall(r"'([^']*)'|(NO_CHANGE)", body.group(1))
    return tuple(change_note.NO_CHANGE if constant else item for item, constant in items)


def test_python_lists_match_the_select_boxes() -> None:
    assert ts_list("PARTS") == change_note.PARTS
    assert ts_list("ACTIONS") == change_note.ACTIONS
    assert ts_list("AMOUNTS") == change_note.AMOUNTS
    assert ts_list("UNITS") == change_note.UNITS
