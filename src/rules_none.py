"""Rules for a bad measurement or no resonance near the target (stage `none`)."""

from collections.abc import Callable, Sequence

from src.impedance import low_freq_gamma_real
from src.models import Diagnosis, Resonance, RuleContext, Stage
from src.rule_tools import LENGTHEN, SHORTEN, amount_text, finding, length_action, target_text
from src.tolerance import at_least, at_most

FEED_FLAT_DB = -1.0
FEED_FLAT_SHARE = 0.9
FEED_GAMMA_LIMIT = 0.5
LOSSY_LOW_DB = -10.0
LOSSY_HIGH_DB = -3.0
LOSSY_SHARE = 0.3


def _share(values: Sequence[float], counts: Callable[[float], bool]) -> float:
    return sum(1 for value in values if counts(value)) / len(values)


def has_positive_s11(ctx: RuleContext) -> bool:
    """A passive antenna cannot reflect more than it receives, so any point above 0 dB is bad."""
    return any(value > 0.0 for value in ctx.sweep.s11_db)


def positive_s11(ctx: RuleContext) -> Diagnosis | None:
    if not has_positive_s11(ctx):
        return None
    evidence = f"S11 최댓값 {max(ctx.sweep.s11_db):+.3g} dB (0 dB보다 큼)"
    action = "OSL 교정을 다시 하고 커넥터 체결을 확인한 뒤 재측정"
    return finding(ctx, "positive_s11", "S11이 0 dB보다 큼", evidence, action)


def has_feed_shape(ctx: RuleContext) -> bool:
    """Shared gate of the feed rules: no resonance anywhere and almost everything reflected."""
    result = ctx.classification
    if result.stage is not Stage.NONE or result.others:
        return False
    flat = _share(ctx.sweep.s11_db, lambda value: not at_most(value, FEED_FLAT_DB))
    return at_least(flat, FEED_FLAT_SHARE)


def _feed_evidence(real: float | None) -> str:
    base = f"거의 모든 점에서 S11이 {FEED_FLAT_DB:g} dB보다 큼"
    if real is None:
        return f"{base}, 복소값 없음"
    return f"{base}, 저주파 반사계수 실수부 {real:+.2f}"


def feed_short(ctx: RuleContext) -> Diagnosis | None:
    real = low_freq_gamma_real(ctx.sweep)
    if not has_feed_shape(ctx) or real is None or at_least(real, -FEED_GAMMA_LIMIT):
        return None
    action = "테스터로 내심-접지 저항 확인, 납땜 브리지 확인"
    return finding(ctx, "feed_short", "급전부가 단락된 것으로 보임", _feed_evidence(real), action)


def feed_open(ctx: RuleContext) -> Diagnosis | None:
    real = low_freq_gamma_real(ctx.sweep)
    if not has_feed_shape(ctx) or real is None or at_most(real, FEED_GAMMA_LIMIT):
        return None
    action = "안테나 선과 내심의 납땜 확인, 범위를 넓혀 재측정"
    return finding(ctx, "feed_open", "급전부가 끊어진 것으로 보임", _feed_evidence(real), action)


def feed_fault(ctx: RuleContext) -> Diagnosis | None:
    real = low_freq_gamma_real(ctx.sweep)
    unclear = real is None or (
        at_least(real, -FEED_GAMMA_LIMIT) and at_most(real, FEED_GAMMA_LIMIT)
    )
    if not has_feed_shape(ctx) or not unclear:
        return None
    action = "내심-접지 저항 확인, 재납땜"
    return finding(ctx, "feed_fault", "급전부 연결 불량", _feed_evidence(real), action)


def lossy(ctx: RuleContext) -> Diagnosis | None:
    result = ctx.classification
    if result.stage is not Stage.NONE or result.others:
        return None
    share = _share(
        ctx.sweep.s11_db,
        lambda value: at_least(value, LOSSY_LOW_DB) and at_most(value, LOSSY_HIGH_DB),
    )
    if not at_least(share, LOSSY_SHARE):
        return None
    evidence = f"S11이 {LOSSY_LOW_DB:g}~{LOSSY_HIGH_DB:g} dB인 점이 {share * 100:.0f} %"
    action = "재납땜, 손·금속에서 띄우고 재측정"
    return finding(ctx, "lossy", "손실이 있을 수 있음", evidence, action)


def far_resonance(ctx: RuleContext) -> Resonance | None:
    """The resonance length_far works from: the one nearest the target when none is selected."""
    result = ctx.classification
    if result.stage is not Stage.NONE or not result.others:
        return None
    return result.others[0]


def length_far(ctx: RuleContext) -> Diagnosis | None:
    nearest = far_resonance(ctx)
    if nearest is None:
        return None
    ratio = nearest.f_mhz / ctx.antenna.target_mhz
    verb = SHORTEN if ratio < 1 else LENGTHEN
    action = length_action(ctx, verb, amount_text(abs(ratio - 1) * 100))
    evidence = f"가장 가까운 공진 {nearest.f_mhz:.2f} MHz, {target_text(ctx)}"
    return finding(ctx, "length_far", "공진이 목표에서 멀리 떨어져 있음", evidence, action)


def out_of_range(ctx: RuleContext) -> Diagnosis | None:
    values, freqs = ctx.sweep.s11_db, ctx.sweep.f_mhz
    if ctx.classification.stage is not Stage.NONE or len(values) < 3:
        return None
    end = 0 if values[0] <= values[-1] else len(values) - 1
    if at_least(values[end], min(values[1:-1])):
        return None
    evidence = f"S11 최솟값 {values[end]:.2f} dB가 측정 범위의 끝 {freqs[end]:.2f} MHz에 있음"
    action = "시작·종료 주파수를 넓혀 재측정"
    return finding(ctx, "out_of_range", "공진이 측정 범위 밖에 있을 수 있음", evidence, action)


def no_resonance(ctx: RuleContext) -> Diagnosis:
    """Fallback for when no rule matched. Not in the rule list; the resolver adds it."""
    values, freqs = ctx.sweep.s11_db, ctx.sweep.f_mhz
    lowest = min(range(len(values)), key=values.__getitem__)
    evidence = f"S11 최솟값 {values[lowest]:.2f} dB ({freqs[lowest]:.2f} MHz)"
    action = "범위를 넓히고 점 수를 늘려 재측정, 납땜과 연결 확인"
    return finding(ctx, "no_resonance", "뚜렷한 공진이 보이지 않음", evidence, action)
