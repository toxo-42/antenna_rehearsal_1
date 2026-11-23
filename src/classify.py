"""Decide the stage of a sweep for one antenna. Stage rules run in order; the first match wins."""

from bisect import bisect_right
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from src.models import (
    CANDIDATE_WINDOW_PCT,
    EXPECTED_WINDOW_PCT,
    TYPICAL_BANDWIDTH_PCT,
    Antenna,
    Band,
    Classification,
    Resonance,
    Stage,
    Sweep,
)
from src.resonance import find_resonances
from src.tolerance import at_least, at_most


@dataclass(frozen=True)
class _Case:
    """What a stage rule may look at: the selected resonance, the antenna, the sweep grid."""

    selected: Resonance
    antenna: Antenna
    f_mhz: tuple[float, ...]

    @property
    def band(self) -> Band:
        if self.selected.band is None:
            raise ValueError("band rules must run after the unmatched rule")
        return self.selected.band


def classify(sweep: Sweep, antenna: Antenna) -> Classification:
    scan = find_resonances(sweep)
    resonances, weak = scan.resonances, scan.weak_dips
    target = antenna.target_mhz
    # With a known conductor length the resonance is looked for where that length should give
    # it: a dip elsewhere (cable, ground plane, a higher mode) is not the antenna's base mode.
    expected = antenna.expected_mhz
    if expected is None:
        selected = _select(resonances, target, CANDIDATE_WINDOW_PCT)
    else:
        selected = _select(resonances, expected, EXPECTED_WINDOW_PCT)
    others = tuple(
        sorted(
            (r for r in resonances if r is not selected),
            key=lambda r: abs(r.f_mhz - target),
        )
    )
    if selected is None:
        return Classification(Stage.NONE, None, None, others, weak)
    case = _Case(selected=selected, antenna=antenna, f_mhz=sweep.f_mhz)
    stage = next((stage for applies, stage in STAGE_RULES if applies(case)), Stage.GOOD)
    offset_pct = (selected.f_mhz - target) / target * 100
    return Classification(stage, selected, offset_pct, others, weak)


def _spacing_at(f_mhz: Sequence[float], edge_mhz: float) -> float:
    """Spacing of the two measured points around a band edge (the last pair at the sweep end)."""
    upper = min(max(bisect_right(f_mhz, edge_mhz), 1), len(f_mhz) - 1)
    return f_mhz[upper] - f_mhz[upper - 1]


def _select(
    resonances: Sequence[Resonance], center_mhz: float, window_pct: float
) -> Resonance | None:
    """Among resonances near the center (the target, or the frequency expected from the length),
    prefer one whose band holds it, then the nearest."""
    window = center_mhz * window_pct / 100
    candidates = [r for r in resonances if at_most(abs(r.f_mhz - center_mhz), window)]
    in_band = [r for r in candidates if r.band is not None and r.band.contains(center_mhz)]
    pool = in_band or candidates
    return min(pool, key=lambda r: abs(r.f_mhz - center_mhz), default=None)


def _is_unmatched(case: _Case) -> bool:
    return case.selected.band is None


def _target_outside_band(case: _Case) -> bool:
    return not case.band.contains(case.antenna.target_mhz)


def _is_narrow(case: _Case) -> bool:
    bandwidth_pct = case.band.width_mhz / case.selected.f_mhz * 100
    return not at_least(bandwidth_pct, TYPICAL_BANDWIDTH_PCT[case.antenna.kind])


def _target_near_band_edge(case: _Case) -> bool:
    target = case.antenna.target_mhz
    low, high = case.band.low_mhz, case.band.high_mhz
    clear_of_low = at_least(target - low, _spacing_at(case.f_mhz, low) / 2)
    clear_of_high = at_least(high - target, _spacing_at(case.f_mhz, high) / 2)
    return not (clear_of_low and clear_of_high)


STAGE_RULES: tuple[tuple[Callable[[_Case], bool], Stage], ...] = (
    (_is_unmatched, Stage.UNMATCHED),
    (_target_outside_band, Stage.OFFTARGET),
    (_is_narrow, Stage.NARROW),
    (_target_near_band_edge, Stage.OFFTARGET),
)
