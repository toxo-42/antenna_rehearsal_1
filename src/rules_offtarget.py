"""Rules for a resonance that misses the target: matched (stage `offtarget`), or shallow and far."""

from src.models import Band, Diagnosis, Resonance, RuleContext, Stage
from src.rule_tools import (
    LENGTHEN,
    SHORTEN,
    amount_text,
    finding,
    length_action,
    length_first,
    length_name,
    target_text,
)


def _offtarget_band(ctx: RuleContext) -> Band | None:
    result = ctx.classification
    if result.stage is not Stage.OFFTARGET or result.selected is None:
        return None
    return result.selected.band


def _missed(ctx: RuleContext) -> Resonance | None:
    """The selected resonance when the target lies outside its band, or when it is shallow and
    far from the target; None otherwise."""
    if length_first(ctx):
        return ctx.classification.selected
    band = _offtarget_band(ctx)
    if band is None or band.contains(ctx.antenna.target_mhz):
        return None
    return ctx.classification.selected


def _offset_pct(ctx: RuleContext) -> float:
    return ctx.classification.offset_pct or 0.0


def _evidence(ctx: RuleContext, resonance: Resonance) -> str:
    return f"공진 {resonance.f_mhz:.2f} MHz, {target_text(ctx)}"


def _length_change(ctx: RuleContext, verb: str) -> str:
    return length_action(ctx, verb, amount_text(abs(_offset_pct(ctx))))


def too_short(ctx: RuleContext) -> Diagnosis | None:
    resonance = _missed(ctx)
    if resonance is None or _offset_pct(ctx) <= 0:
        return None
    title = f"{length_name(ctx)}가 짧음"
    action = _length_change(ctx, LENGTHEN)
    return finding(ctx, "too_short", title, _evidence(ctx, resonance), action)


def too_long(ctx: RuleContext) -> Diagnosis | None:
    resonance = _missed(ctx)
    if resonance is None or _offset_pct(ctx) >= 0:
        return None
    title = f"{length_name(ctx)}가 김"
    action = _length_change(ctx, SHORTEN)
    return finding(ctx, "too_long", title, _evidence(ctx, resonance), action)


def feed_lead(ctx: RuleContext) -> Diagnosis | None:
    resonance = _missed(ctx)
    if resonance is None or _offset_pct(ctx) >= 0:
        return None
    title = "급전부의 노출된 선이 김"
    return finding(ctx, "feed_lead", title, _evidence(ctx, resonance), "노출된 급전선을 짧게")


def band_edge(ctx: RuleContext) -> Diagnosis | None:
    band = _offtarget_band(ctx)
    if band is None or not band.contains(ctx.antenna.target_mhz):
        return None
    evidence = f"대역 {band.low_mhz:.2f}~{band.high_mhz:.2f} MHz, {target_text(ctx)}"
    action = "목표 주변을 더 촘촘한 간격으로 재측정. 길이는 아직 바꾸지 말 것"
    return finding(ctx, "band_edge", "목표가 정합 대역의 끝에 가까움", evidence, action)
