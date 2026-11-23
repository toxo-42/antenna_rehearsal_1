"""A resonance measured with too few points: the note and the narrower range to measure again.

This is not a diagnosis rule. It goes to the card's `remeasure` field, next to the diagnoses.
"""

import math

from src.models import (
    MIN_STEPS_ACROSS_RESONANCE,
    REMEASURE_SPAN_PCT,
    TYPICAL_BANDWIDTH_PCT,
    Remeasure,
    Resonance,
    RuleContext,
)
from src.rule_tools import step_at
from src.rules_none import has_positive_s11
from src.tolerance import ABS_TOL, at_least


def _width_mhz(ctx: RuleContext, selected: Resonance) -> float:
    """How wide the resonance is: its matched band, or the usual bandwidth of this antenna kind
    when it is too shallow to have one."""
    if selected.band is not None:
        return selected.band.width_mhz
    return selected.f_mhz * TYPICAL_BANDWIDTH_PCT[ctx.antenna.kind] / 100


def _is_coarse(ctx: RuleContext, selected: Resonance) -> bool:
    step = step_at(ctx, selected.index)
    return step > 0 and not at_least(_width_mhz(ctx, selected) / step, MIN_STEPS_ACROSS_RESONANCE)


def _round_half_up(value: float) -> int:
    """Whole MHz with a half going up (Python's round() sends 402.5 down to the even 402)."""
    return math.floor(value + 0.5 + ABS_TOL)  # 402.49999999999994 is a computed 402.5


def _range_with_target(resonance_mhz: float, target_mhz: float) -> tuple[int, int]:
    """REMEASURE_SPAN_PCT to each side of the resonance in whole MHz, widened where needed so
    that the target is inside: the server refuses a sweep that leaves the target out."""
    span = resonance_mhz * REMEASURE_SPAN_PCT / 100
    start, stop = _round_half_up(resonance_mhz - span), _round_half_up(resonance_mhz + span)
    return min(start, math.floor(target_mhz)), max(stop, math.ceil(target_mhz))


def remeasure_range(ctx: RuleContext) -> Remeasure | None:
    """The range to measure again when the selected resonance has too few points across it.
    None for a sweep that cannot be judged (positive S11) or without a selected resonance."""
    selected = ctx.classification.selected
    if selected is None or has_positive_s11(ctx) or not _is_coarse(ctx, selected):
        return None
    start, stop = _range_with_target(selected.f_mhz, ctx.antenna.target_mhz)
    if start >= stop:
        return None
    step, width = step_at(ctx, selected.index), _width_mhz(ctx, selected)
    note = (
        f"측정 점이 성겨서 공진 주파수와 S11 값이 정확하지 않을 수 있습니다 "
        f"(공진 근처 간격 {step:.2f} MHz, 공진 폭 약 {width:.2f} MHz). "
        f"{start}~{stop} MHz 범위로 좁혀서 다시 측정해 보세요."
    )
    return Remeasure(start_mhz=start, stop_mhz=stop, note=note)
