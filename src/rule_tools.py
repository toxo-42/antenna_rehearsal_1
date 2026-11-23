"""Shared pieces for diagnosis rules: the rule signature, text formats, and Diagnosis assembly."""

from collections.abc import Callable

from src.guides import guide_for
from src.models import (
    FIFTH_MODE_MAX_RATIO,
    FIFTH_MODE_MIN_RATIO,
    LENGTH_FIRST_PCT,
    THIRD_MODE_MAX_RATIO,
    THIRD_MODE_MIN_RATIO,
    AntennaKind,
    Diagnosis,
    RuleContext,
    Stage,
)
from src.tolerance import ABS_TOL, at_least, at_most

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


def step_at(ctx: RuleContext, index: int) -> float:
    """The coarser of the two measurement gaps beside point `index`, in MHz."""
    freqs = ctx.sweep.f_mhz
    low, high = max(index - 1, 0), min(index + 1, len(freqs) - 1)
    return max(freqs[index] - freqs[low], freqs[high] - freqs[index])


def length_first(ctx: RuleContext) -> bool:
    """True for a shallow resonance far enough from the target to fix the length first: at least
    LENGTH_FIRST_PCT away, and at least one measurement step (a smaller miss is not resolved)."""
    result = ctx.classification
    selected, offset_pct = result.selected, result.offset_pct
    if result.stage is not Stage.UNMATCHED or selected is None or offset_pct is None:
        return False
    distance = abs(selected.f_mhz - ctx.antenna.target_mhz)
    far = at_least(abs(offset_pct), LENGTH_FIRST_PCT)
    return far and at_least(distance, step_at(ctx, selected.index))


def _ratio_within(upper_mhz: float, lower_mhz: float, limits: tuple[float, float]) -> bool:
    if lower_mhz <= 0 or lower_mhz >= upper_mhz:
        return False
    ratio = upper_mhz / lower_mhz
    return at_least(ratio, limits[0]) and at_most(ratio, limits[1])


def in_third_ratio(upper_mhz: float, lower_mhz: float) -> bool:
    """True when `upper_mhz` is about three times `lower_mhz` (a monopole's third mode)."""
    return _ratio_within(upper_mhz, lower_mhz, (THIRD_MODE_MIN_RATIO, THIRD_MODE_MAX_RATIO))


def in_fifth_ratio(upper_mhz: float, lower_mhz: float) -> bool:
    """True when `upper_mhz` is about five times `lower_mhz` (a monopole's fifth mode)."""
    return _ratio_within(upper_mhz, lower_mhz, (FIFTH_MODE_MIN_RATIO, FIFTH_MODE_MAX_RATIO))


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
