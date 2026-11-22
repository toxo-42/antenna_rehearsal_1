"""Rules for a resonance that is too shallow to count as matched (stage `unmatched`)."""

from src.impedance import impedance_at, reactance_at
from src.models import AntennaKind, Diagnosis, Impedance, RuleContext, Stage
from src.rule_tools import LENGTH_CAUTION, LENGTHEN, SHORTEN, finding, length_name, target_text
from src.tolerance import at_least, at_most

R_LOW_OHM = 30.0
R_HIGH_OHM = 90.0
QUARTER_WAVE_CM_MHZ = 7500.0
RETEST_FINER = "더 촘촘한 간격으로 재측정"

R_LOW_ACTION: dict[AntennaKind, str] = {
    AntennaKind.MONOPOLE: "접지판을 λ/4(약 {quarter_cm:.1f} cm) 이상으로 키우고 라디알 추가",
    AntennaKind.PATCH: "급전점을 가장자리 쪽으로 옮기기",
}
R_HIGH_ACTION: dict[AntennaKind, str] = {
    AntennaKind.MONOPOLE: "접지판과 커넥터 접지의 납땜·접촉 확인",
    AntennaKind.PATCH: "급전점을 중심 쪽으로 옮기기",
}


def _is_unmatched(ctx: RuleContext) -> bool:
    return ctx.classification.stage is Stage.UNMATCHED


def _impedance(ctx: RuleContext) -> Impedance | None:
    """Impedance at the unmatched resonance; None for other stages or without complex data."""
    selected = ctx.classification.selected
    if not _is_unmatched(ctx) or selected is None:
        return None
    return impedance_at(ctx.sweep, selected.index)


def _r_text(impedance: Impedance) -> str:
    return f"공진점 R {impedance.r_ohm:.2f} Ω"


def r_low(ctx: RuleContext) -> Diagnosis | None:
    impedance = _impedance(ctx)
    if impedance is None or at_least(impedance.r_ohm, R_LOW_OHM):
        return None
    quarter_cm = QUARTER_WAVE_CM_MHZ / ctx.antenna.target_mhz
    action = R_LOW_ACTION[ctx.antenna.kind].format(quarter_cm=quarter_cm)
    evidence = f"{_r_text(impedance)} (기준 {R_LOW_OHM:g} Ω 미만)"
    return finding(ctx, "r_low", "입력 저항이 낮음", evidence, action)


def r_high(ctx: RuleContext) -> Diagnosis | None:
    impedance = _impedance(ctx)
    if impedance is None or at_most(impedance.r_ohm, R_HIGH_OHM):
        return None
    evidence = f"{_r_text(impedance)} (기준 {R_HIGH_OHM:g} Ω 초과)"
    return finding(ctx, "r_high", "입력 저항이 높음", evidence, R_HIGH_ACTION[ctx.antenna.kind])


def _is_zero(value: float) -> bool:
    return at_least(value, 0.0) and at_most(value, 0.0)


def _reactance_action(ctx: RuleContext, x_ohm: float | None) -> str:
    """Direction from X at the target: inductive means too long, capacitive means too short."""
    if x_ohm is None or _is_zero(x_ohm):
        return RETEST_FINER
    verb = SHORTEN if x_ohm > 0 else LENGTHEN
    return f"{length_name(ctx)}를 조금 {verb} 미세 조정이 {LENGTH_CAUTION}"


def _reactance_evidence(ctx: RuleContext, impedance: Impedance, x_ohm: float | None) -> str:
    if x_ohm is None:
        return f"{_r_text(impedance)}, 목표가 측정 범위 밖이라 목표점 X를 알 수 없음"
    return f"{_r_text(impedance)}, {target_text(ctx)}에서 X {x_ohm:+.2f} Ω"


def reactance(ctx: RuleContext) -> Diagnosis | None:
    impedance = _impedance(ctx)
    if impedance is None:
        return None
    if not (at_least(impedance.r_ohm, R_LOW_OHM) and at_most(impedance.r_ohm, R_HIGH_OHM)):
        return None
    x_ohm = reactance_at(ctx.sweep, ctx.antenna.target_mhz)
    evidence = _reactance_evidence(ctx, impedance, x_ohm)
    action = _reactance_action(ctx, x_ohm)
    return finding(ctx, "reactance", "리액턴스가 남아 있음", evidence, action)


def match_unknown(ctx: RuleContext) -> Diagnosis | None:
    if not _is_unmatched(ctx) or ctx.sweep.gamma is not None:
        return None
    action = "복소값이 있는 측정으로 다시, 접지판과 납땜 확인"
    return finding(ctx, "match_unknown", "정합이 얕은 원인을 알 수 없음", "복소값 없음", action)


def common_mode(ctx: RuleContext) -> Diagnosis | None:
    selected = ctx.classification.selected
    if not _is_unmatched(ctx) or selected is None:
        return None
    evidence = f"공진 {selected.f_mhz:.2f} MHz에서 S11 {selected.s11_db:.2f} dB"
    action = "케이블을 잡아 보고 변하면 접지판 확대·페라이트"
    return finding(ctx, "common_mode", "케이블에 전류가 흐를 수 있음", evidence, action)
