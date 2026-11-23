"""What each card stage means, as sentences built from the rule constants.

The screen shows these next to the verdict as they are. A number is never written here by hand:
when a threshold in `models` changes, the sentence changes with it.
"""

from collections.abc import Callable

from src import models
from src.models import AntennaKind, CardStage
from src.service import InputError

KIND_NAME = {AntennaKind.MONOPOLE: "모노폴", AntennaKind.PATCH: "패치"}

Sentence = Callable[[AntennaKind], str]


def _band() -> str:
    return f"S11 {models.MATCH_THRESHOLD_DB:g} dB 이하인 대역"


def _good(kind: AntennaKind) -> str:
    width = models.TYPICAL_BANDWIDTH_PCT[kind]
    return (
        f"목표 주파수가 {_band()} 안에 있고, 그 대역의 폭이 공진 주파수의 {width:g} % 이상입니다."
    )


def _narrow(kind: AntennaKind) -> str:
    width = models.TYPICAL_BANDWIDTH_PCT[kind]
    return (
        f"목표 주파수는 {_band()} 안에 있지만, 대역의 폭이 공진 주파수의 "
        f"{width:g} %({KIND_NAME[kind]} 기준)보다 좁습니다."
    )


def _offtarget(kind: AntennaKind) -> str:
    return (
        f"공진은 {_band()}을 만들지만, 목표 주파수가 그 대역 밖에 있거나 대역 끝에 걸쳐 있습니다."
    )


def _unmatched(kind: AntennaKind) -> str:
    return (
        f"목표 근처에 공진은 있지만 S11이 {models.MATCH_THRESHOLD_DB:g} dB까지 내려가지 않습니다."
    )


def _none(kind: AntennaKind) -> str:
    text = (
        f"목표 주파수의 ±{models.CANDIDATE_WINDOW_PCT:g} % 안에 공진이 없습니다. 공진은 주변보다 "
        f"{models.RESONANCE_MIN_DEPTH_DB:g} dB 이상 깊고 S11이 {models.RESONANCE_MAX_S11_DB:g} dB 이하인 골입니다."
    )
    if kind is not AntennaKind.MONOPOLE:
        return text
    return (
        f"{text} 도체 길이를 넣었으면 목표 대신 그 길이의 예상 주파수"
        f"({models.QUARTER_WAVE_CM_MHZ:g} ÷ 길이 cm, MHz)의 ±{models.EXPECTED_WINDOW_PCT:g} % 안에서 찾습니다."
    )


def _invalid(kind: AntennaKind) -> str:
    return (
        f"S11이 +{models.POSITIVE_S11_DB:g} dB를 넘는 점이 있어 판정하지 않습니다. "
        "교정이나 연결을 확인해야 합니다."
    )


# From the best state to the worst; the screen groups them under 양호, 주의, 문제.
SENTENCES: tuple[tuple[CardStage, Sentence], ...] = (
    (CardStage.GOOD, _good),
    (CardStage.NARROW, _narrow),
    (CardStage.OFFTARGET, _offtarget),
    (CardStage.UNMATCHED, _unmatched),
    (CardStage.NONE, _none),
    (CardStage.INVALID, _invalid),
)


def stage_criteria(kind: AntennaKind) -> list[dict[str, str]]:
    """One sentence per card stage for this kind of antenna."""
    return [{"stage": stage.value, "text": sentence(kind)} for stage, sentence in SENTENCES]


def criteria_for(kind: str) -> list[dict[str, str]]:
    """`stage_criteria` for a kind given as text; an unknown kind is an input error."""
    allowed = [item.value for item in AntennaKind]
    if kind not in allowed:
        raise InputError(f"kind는 {', '.join(allowed)} 중 하나여야 합니다 (받은 값: '{kind}').")
    return stage_criteria(AntennaKind(kind))
