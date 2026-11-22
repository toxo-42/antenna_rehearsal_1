"""Shared pieces for diagnosis rules: the rule signature, text formats, and Diagnosis assembly."""

from collections.abc import Callable

from src.guides import guide_for
from src.models import AntennaKind, Diagnosis, RuleContext
from src.tolerance import ABS_TOL

Rule = Callable[[RuleContext], Diagnosis | None]

SHORTEN = "줄이는"
LENGTHEN = "늘리는"
# "Check before cutting" on a lengthen action reads as "cut" to students and to the LLM.
LENGTH_CAUTION: dict[str, str] = {
    SHORTEN: "초기 추정. 한 번에 절반씩, 자르기 전에 다시 측정",
    LENGTHEN: "초기 추정. 한 번에 절반씩, 자르지 말고 덧붙여서 확인",
}
LENGTH_NAME: dict[AntennaKind, str] = {
    AntennaKind.MONOPOLE: "안테나 도체",
    AntennaKind.PATCH: "패치 길이(공진 방향 변)",
}


def finding(ctx: RuleContext, key: str, title: str, evidence: str, action: str) -> Diagnosis:
    """Assemble one diagnosis; the guide sentence always comes from the fixed table."""
    guide = guide_for(key, ctx.antenna.kind)
    return Diagnosis(key=key, title=title, evidence=evidence, action=action, guide=guide)


def length_name(ctx: RuleContext) -> str:
    return LENGTH_NAME[ctx.antenna.kind]


def target_text(ctx: RuleContext) -> str:
    return f"목표 {ctx.antenna.target_mhz:g} MHz"


def amount_text(pct: float) -> str:
    """Adjustment size as text: a whole percent rounded half up, or "1 % 미만" when it rounds to 0."""
    rounded = int(pct + 0.5 + ABS_TOL)  # 25.49999999999999 is a computed 25.5
    if rounded == 0:
        return "1 % 미만"
    return f"약 {rounded} %"


def length_caution(verb: str) -> str:
    """The "first estimate, half at a time" caution for a SHORTEN or LENGTHEN action."""
    return LENGTH_CAUTION[verb]


def length_action(ctx: RuleContext, verb: str, amount: str) -> str:
    """A length change sentence. It always carries the caution for its direction."""
    return f"{length_name(ctx)}를 {amount} {verb} 것이 {length_caution(verb)}"
