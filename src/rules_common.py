"""Rules that are not tied to one failing stage: extra resonances, narrow, good, calibration."""

from src.models import (
    TYPICAL_BANDWIDTH_PCT,
    AntennaKind,
    CalMode,
    Diagnosis,
    Resonance,
    RuleContext,
    Stage,
)
from src.rule_tools import LENGTH_CAUTION, SHORTEN, finding, length_name
from src.rules_none import far_resonance, has_positive_s11
from src.tolerance import at_least, at_most

THIRD_MODE_MIN_RATIO = 2.6
THIRD_MODE_MAX_RATIO = 3.4

NARROW_ACTION: dict[AntennaKind, str] = {
    AntennaKind.MONOPOLE: "안테나 도체를 굵게",
    AntennaKind.PATCH: "기판을 두껍게 하거나 유전율이 낮은 기판으로 교체",
}


def _is_base_of(selected: Resonance, other: Resonance) -> bool:
    """True when `other` is a lower matched resonance about a third of the selected one."""
    if other.band is None or other.f_mhz >= selected.f_mhz:
        return False
    ratio = selected.f_mhz / other.f_mhz
    return at_least(ratio, THIRD_MODE_MIN_RATIO) and at_most(ratio, THIRD_MODE_MAX_RATIO)


def third_mode_base(ctx: RuleContext) -> Resonance | None:
    """The lower resonance that makes the selected one look like a monopole's third mode."""
    selected = ctx.classification.selected
    if ctx.antenna.kind is not AntennaKind.MONOPOLE or selected is None:
        return None
    return next((r for r in ctx.classification.others if _is_base_of(selected, r)), None)


def third_mode(ctx: RuleContext) -> Diagnosis | None:
    selected, base = ctx.classification.selected, third_mode_base(ctx)
    if selected is None or base is None:
        return None
    ratio = selected.f_mhz / base.f_mhz
    evidence = f"공진 {selected.f_mhz:.2f} MHz는 더 낮은 공진 {base.f_mhz:.2f} MHz의 {ratio:.2f}배"
    action = (
        f"기본 모드로 맞추려면 {length_name(ctx)}를 약 1/3로 {SHORTEN} 것이 {LENGTH_CAUTION}. "
        "확신 없이 자르지 말 것"
    )
    return finding(ctx, "third_mode", "3배 모드 공진일 수 있음", evidence, action)


def other_resonance(ctx: RuleContext) -> Diagnosis | None:
    if third_mode_base(ctx) is not None:
        return None
    used = far_resonance(ctx)
    matched = (r for r in ctx.classification.others if r.band is not None and r is not used)
    extra = next(matched, None)
    if extra is None:
        return None
    evidence = f"다른 공진 {extra.f_mhz:.2f} MHz (S11 {extra.s11_db:.2f} dB)"
    action = "케이블 위치를 바꾸거나 페라이트를 끼운 뒤 재측정"
    return finding(ctx, "other_resonance", "다른 주파수에도 공진이 있음", evidence, action)


def narrow(ctx: RuleContext) -> Diagnosis | None:
    selected = ctx.classification.selected
    if ctx.classification.stage is not Stage.NARROW or selected is None:
        return None
    typical = TYPICAL_BANDWIDTH_PCT[ctx.antenna.kind]
    evidence = f"대역 폭 {selected.bandwidth_pct or 0.0:.2f} % (기준 {typical:g} %)"
    return finding(ctx, "narrow", "대역이 좁음", evidence, NARROW_ACTION[ctx.antenna.kind])


def good(ctx: RuleContext) -> Diagnosis | None:
    selected = ctx.classification.selected
    if ctx.classification.stage is not Stage.GOOD or selected is None:
        return None
    evidence = f"공진 {selected.f_mhz:.2f} MHz, S11 {selected.s11_db:.2f} dB"
    action = "손·케이블 위치를 바꿔도 유지되는지 확인하고 저장"
    return finding(ctx, "good", "목표에서 잘 동작함", evidence, action)


def uncalibrated(ctx: RuleContext) -> Diagnosis | None:
    if ctx.cal_mode is not CalMode.UNKNOWN or has_positive_s11(ctx):
        return None
    action = (
        "수치는 경향 참고용. 교정된 측정으로 다시 확인 "
        "(USB로 받은 값에는 장비의 교정이 반영되지 않는다)"
    )
    return finding(ctx, "uncalibrated", "교정이 확인되지 않음", "교정 상태를 알 수 없음", action)
