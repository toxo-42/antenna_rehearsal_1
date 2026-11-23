"""Rules for a bad measurement or no resonance near the target (stage `none`)."""

from collections.abc import Callable, Sequence

from src.impedance import low_freq_gamma_real
from src.models import (
    EXPECTED_WINDOW_PCT,
    POSITIVE_S11_DB,
    AntennaKind,
    Diagnosis,
    Dip,
    Resonance,
    RuleContext,
    Stage,
)
from src.rule_tools import (
    LENGTHEN,
    SHORTEN,
    amount_text,
    finding,
    in_third_ratio,
    length_action,
    target_text,
)
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
    """A passive antenna cannot reflect more than it receives. Small positives near 0 dB are
    noise, so only a point above POSITIVE_S11_DB (no tolerance) marks the sweep as bad."""
    return any(value > POSITIVE_S11_DB for value in ctx.sweep.s11_db)


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


def weak_base(ctx: RuleContext) -> Dip | None:
    """A monopole's weak dip about a third of the judged resonance (the selected one, or the far
    one when none is selected): the base mode, too weak to count as a resonance."""
    result = ctx.classification
    judged = result.selected or far_resonance(ctx)
    if ctx.antenna.kind is not AntennaKind.MONOPOLE or judged is None:
        return None
    return next((d for d in result.weak_dips if in_third_ratio(judged.f_mhz, d.f_mhz)), None)


def expected_window(ctx: RuleContext) -> tuple[float, float] | None:
    """Where the base resonance should be for the entered length; None without a length."""
    expected = ctx.antenna.expected_mhz
    if expected is None:
        return None
    half = expected * EXPECTED_WINDOW_PCT / 100
    return expected - half, expected + half


def expected_weak_dip(ctx: RuleContext) -> Dip | None:
    """The weak dip nearest the expected frequency when no resonance was found there."""
    window, expected = expected_window(ctx), ctx.antenna.expected_mhz
    if window is None or expected is None or ctx.classification.stage is not Stage.NONE:
        return None
    low, high = window
    near = [d for d in ctx.classification.weak_dips if at_least(d.f_mhz, low)]
    near = [d for d in near if at_most(d.f_mhz, high)]
    return min(near, key=lambda d: abs(d.f_mhz - expected), default=None)


def length_text(ctx: RuleContext) -> str:
    """ "길이 12 cm의 예상 공진 625.00 MHz" for evidence lines; only called with a length."""
    return f"길이 {ctx.antenna.length_cm:g} cm의 예상 공진 {ctx.antenna.expected_mhz:.2f} MHz"


def missing_fundamental(ctx: RuleContext) -> Diagnosis | None:
    window, expected = expected_window(ctx), ctx.antenna.expected_mhz
    if window is None or expected is None or ctx.classification.stage is not Stage.NONE:
        return None
    if expected_weak_dip(ctx) is not None or has_feed_shape(ctx):
        return None
    evidence = f"{length_text(ctx)} 근처({window[0]:.0f}~{window[1]:.0f} MHz)에 공진이 없음"
    covered = at_least(expected, ctx.sweep.f_mhz[0]) and at_most(expected, ctx.sweep.f_mhz[-1])
    action = (
        "급전부 납땜과 접지 연결을 확인한 뒤 재측정. 길이는 아직 바꾸지 말 것"
        if covered
        else f"예상 공진 {expected:.0f} MHz가 들어가도록 측정 범위를 넓혀 재측정"
    )
    return finding(ctx, "missing_fundamental", "이 길이의 공진이 보이지 않음", evidence, action)


def length_far(ctx: RuleContext) -> Diagnosis | None:
    nearest = far_resonance(ctx)
    # A third mode, or a dip away from where this length resonates, says nothing about length.
    if nearest is None or weak_base(ctx) is not None or expected_window(ctx) is not None:
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
