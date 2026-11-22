"""Guide sentences must be exactly the ones fixed in spec/p2_diagnosis.md."""

import json
import re
from pathlib import Path

import pytest

from src.guides import GUIDES, guide_for
from src.models import AntennaKind

SPEC = Path(__file__).resolve().parent.parent / "spec" / "p2_diagnosis.md"
BY_KIND = ("length_far", "too_short", "too_long", "r_low", "r_high", "narrow")


def spec_guides() -> dict[str, str | dict[str, str]]:
    text = SPEC.read_text(encoding="utf-8")
    block = re.search(r"```json\n(.*?)```", text, re.DOTALL)
    assert block is not None
    return json.loads(block.group(1))


def test_guides_match_the_spec_word_for_word() -> None:
    assert GUIDES == spec_guides()


def test_spec_has_a_sentence_per_kind_for_the_split_keys() -> None:
    spec = spec_guides()

    assert sorted(k for k, v in spec.items() if isinstance(v, dict)) == sorted(BY_KIND)


@pytest.mark.parametrize("key", BY_KIND)
@pytest.mark.parametrize("kind", list(AntennaKind))
def test_guide_for_picks_the_sentence_for_the_antenna_kind(key: str, kind: AntennaKind) -> None:
    sentences = spec_guides()[key]
    assert isinstance(sentences, dict)

    assert guide_for(key, kind) == sentences[kind.value]


@pytest.mark.parametrize("kind", list(AntennaKind))
def test_guide_for_returns_the_shared_sentence_for_other_keys(kind: AntennaKind) -> None:
    assert guide_for("good", kind) == spec_guides()["good"]
    assert guide_for("no_resonance", kind) == spec_guides()["no_resonance"]
