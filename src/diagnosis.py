"""Run the diagnosis rules in order. One rule = one function; add a rule by adding a function."""

from src.classify import classify
from src.models import Antenna, CalMode, Diagnosis, RuleContext, Sweep
from src.rule_tools import Rule
from src.rules_common import (
    good,
    narrow,
    other_resonance,
    third_mode,
    uncalibrated,
    weak_fundamental,
)
from src.rules_none import (
    feed_fault,
    feed_open,
    feed_short,
    length_far,
    lossy,
    missing_fundamental,
    no_resonance,
    out_of_range,
    positive_s11,
)
from src.rules_offtarget import band_edge, feed_lead, too_long, too_short
from src.rules_unmatched import common_mode, match_unknown, r_high, r_low, reactance

RULES: tuple[Rule, ...] = (
    positive_s11,
    feed_short,
    feed_open,
    feed_fault,
    lossy,
    length_far,
    weak_fundamental,
    missing_fundamental,
    out_of_range,
    too_short,
    too_long,
    feed_lead,
    band_edge,
    r_low,
    r_high,
    reactance,
    match_unknown,
    common_mode,
    third_mode,
    other_resonance,
    narrow,
    good,
    uncalibrated,
)

ONLY_ALONE = "positive_s11"
HIDES_OUT_OF_RANGE = frozenset({"feed_short", "feed_open", "feed_fault", "lossy"})
HIDDEN_BY_THEM = "out_of_range"
NOT_A_FINDING = "uncalibrated"


def context_for(sweep: Sweep, antenna: Antenna, cal_mode: CalMode) -> RuleContext:
    """Classify the sweep and bundle what the rules may read."""
    return RuleContext(
        classification=classify(sweep, antenna), sweep=sweep, antenna=antenna, cal_mode=cal_mode
    )


def diagnose(ctx: RuleContext) -> tuple[Diagnosis, ...]:
    """Every matching diagnosis in rule order, after the exclusive rules and the fallback."""
    found = tuple(result for rule in RULES if (result := rule(ctx)) is not None)
    return _resolve(ctx, found)


def _resolve(ctx: RuleContext, found: tuple[Diagnosis, ...]) -> tuple[Diagnosis, ...]:
    """The only place that looks at the result list: two exclusive rules and one fallback."""
    keys = {result.key for result in found}
    if ONLY_ALONE in keys:
        return tuple(result for result in found if result.key == ONLY_ALONE)
    if keys & HIDES_OUT_OF_RANGE:
        found = tuple(result for result in found if result.key != HIDDEN_BY_THEM)
    if all(result.key == NOT_A_FINDING for result in found):
        found = (no_resonance(ctx), *found)
    return found
