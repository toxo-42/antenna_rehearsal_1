"""Build the verdict card: stage, headline, status lines, and diagnoses. All text comes from code."""

import math
from collections.abc import Callable
from itertools import pairwise

from src.diagnosis import context_for, diagnose
from src.impedance import impedance_at
from src.models import Antenna, CalMode, Card, CardStage, RuleContext, Sweep
from src.rule_tools import length_first
from src.rules_none import has_positive_s11
from src.rules_step import remeasure_range

HEADLINES: dict[CardStage, str] = {
    CardStage.NONE: "목표 근처에서 공진을 찾지 못했습니다",
    CardStage.UNMATCHED: "공진은 있지만 정합이 얕습니다",
    CardStage.OFFTARGET: "공진은 있지만 목표 주파수에 맞지 않습니다",
    CardStage.NARROW: "목표에서 공진하지만 대역이 좁습니다",
    CardStage.GOOD: "목표 주파수에서 잘 동작합니다",
    CardStage.INVALID: "측정값이 올바르지 않아 판정할 수 없습니다",
}
# A diagnosis that makes the stage sentence misleading replaces it. The stage itself stays.
HEADLINE_FOR_KEY: dict[str, str] = {
    "band_edge": "목표가 대역 끝에 가까워 이 측정 간격으로는 확정할 수 없습니다",
    "missing_fundamental": "이 길이라면 있어야 할 공진이 보이지 않습니다",
}
LENGTH_FIRST_HEADLINE = "공진이 목표 주파수에서 벗어나 있고 정합도 얕습니다"
CAL_TEXT: dict[CalMode, str] = {
    CalMode.VNA: "VNA에서 교정함",
    CalMode.UNKNOWN: "모름 / 안 함",
}

StatusLine = Callable[[RuleContext], str | None]


def build_card(sweep: Sweep, antenna: Antenna, cal_mode: CalMode) -> Card:
    """Judge one sweep for one antenna and return the card shown to the student."""
    ctx = context_for(sweep, antenna, cal_mode)
    stage, diagnoses = _card_stage(ctx), diagnose(ctx)
    special = (HEADLINE_FOR_KEY[d.key] for d in diagnoses if d.key in HEADLINE_FOR_KEY)
    usual = LENGTH_FIRST_HEADLINE if length_first(ctx) else HEADLINES[stage]
    headline = next(special, usual)
    status = tuple(text for line in STATUS_LINES if (text := line(ctx)) is not None)
    return Card(stage, headline, status, diagnoses, remeasure_range(ctx))


def _card_stage(ctx: RuleContext) -> CardStage:
    if has_positive_s11(ctx):
        return CardStage.INVALID
    return CardStage(ctx.classification.stage.value)


def _resonance_line(ctx: RuleContext) -> str:
    result = ctx.classification
    if result.selected is None or result.offset_pct is None:
        where = "목표" if ctx.antenna.expected_mhz is None else "예상 주파수"
        return f"{where} 근처에 공진 없음"
    f_mhz = result.selected.f_mhz
    offset_mhz = f_mhz - ctx.antenna.target_mhz
    return f"공진 {f_mhz:.2f} MHz (목표 {offset_mhz:+.2f} MHz, {result.offset_pct:+.2f} %)"


def _expected_line(ctx: RuleContext) -> str | None:
    expected = ctx.antenna.expected_mhz
    if expected is None:
        return None
    return f"예상 공진 {expected:.2f} MHz (도체 길이 {ctx.antenna.length_cm:g} cm)"


def _depth_line(ctx: RuleContext) -> str | None:
    selected = ctx.classification.selected
    if selected is None:
        return None
    return f"S11 {selected.s11_db:.2f} dB (깊이 {selected.depth_db:.2f} dB)"


def _band_line(ctx: RuleContext) -> str | None:
    selected = ctx.classification.selected
    if selected is None or selected.band is None or selected.bandwidth_pct is None:
        return None
    band = selected.band
    return f"대역 {band.low_mhz:.2f}~{band.high_mhz:.2f} MHz (폭 {selected.bandwidth_pct:.2f} %)"


def _impedance_line(ctx: RuleContext) -> str | None:
    selected = ctx.classification.selected
    if selected is None:
        return None
    impedance = impedance_at(ctx.sweep, selected.index)
    if impedance is None or not all(map(math.isfinite, (impedance.r_ohm, impedance.x_ohm))):
        return None
    return f"공진점 R {impedance.r_ohm:.2f} Ω, X {impedance.x_ohm:+.2f} Ω"


def _cal_line(ctx: RuleContext) -> str:
    return f"교정: {CAL_TEXT[ctx.cal_mode]}"


def _spacing_line(ctx: RuleContext) -> str | None:
    freqs = ctx.sweep.f_mhz
    steps = [upper - lower for lower, upper in pairwise(freqs)]
    if not steps:
        return None
    narrowest, widest = f"{min(steps):.2f}", f"{max(steps):.2f}"
    if narrowest == widest:
        return f"측정 간격 {narrowest} MHz"
    return f"측정 간격 {narrowest}~{widest} MHz"


STATUS_LINES: tuple[StatusLine, ...] = (
    _resonance_line,
    _expected_line,
    _depth_line,
    _band_line,
    _impedance_line,
    _cal_line,
    _spacing_line,
)
