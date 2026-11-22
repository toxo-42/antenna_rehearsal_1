"""Find resonances in an S11 sweep: local minima, their depth, and the matched band around them."""

from collections.abc import Sequence

from src.models import (
    MATCH_THRESHOLD_DB,
    RESONANCE_MAX_S11_DB,
    RESONANCE_MIN_DEPTH_DB,
    WEAK_DIP_MIN_DEPTH_DB,
    Band,
    Dip,
    Resonance,
    ResonanceScan,
    Sweep,
)
from src.tolerance import at_least, at_most


def find_resonances(sweep: Sweep) -> ResonanceScan:
    """Sort every local minimum into resonance, weak dip, or a minor dip that is only counted."""
    values = sweep.s11_db
    left = _shoulders(values)
    right = _shoulders(values[::-1])[::-1]
    dips = [
        Dip(
            index=i, f_mhz=sweep.f_mhz[i], s11_db=values[i], depth_db=_depth(values, i, left, right)
        )
        for i in _local_minima(values)
    ]
    runs = _matched_runs(values)
    resonances = tuple(_with_band(sweep, dip, runs) for dip in dips if _is_resonance(dip))
    weak_dips = tuple(dip for dip in dips if _is_weak_dip(dip))
    return ResonanceScan(
        resonances=resonances,
        weak_dips=weak_dips,
        minor_count=len(dips) - len(resonances) - len(weak_dips),
    )


def _local_minima(values: Sequence[float]) -> list[int]:
    return [
        i
        for i in range(1, len(values) - 1)
        if values[i] < values[i - 1] and values[i] <= values[i + 1]
    ]


def _shoulders(values: Sequence[float]) -> list[float]:
    """For each point, the highest value walking left until a point lower than it (or the end).

    One pass with a stack: each entry keeps its value and the highest value since the entry
    below it, so points that cannot stop a later walk are merged instead of walked again.
    """
    stack: list[tuple[float, float]] = []
    peaks: list[float] = []
    for value in values:
        peak = value
        while stack and stack[-1][0] >= value:
            peak = max(peak, stack.pop()[1])
        peaks.append(peak)
        stack.append((value, peak))
    return peaks


def _depth(values: Sequence[float], index: int, left: list[float], right: list[float]) -> float:
    return min(left[index], right[index]) - values[index]


def _is_resonance(dip: Dip) -> bool:
    deep_enough = at_least(dip.depth_db, RESONANCE_MIN_DEPTH_DB)
    return deep_enough and at_most(dip.s11_db, RESONANCE_MAX_S11_DB)


def _is_weak_dip(dip: Dip) -> bool:
    return not _is_resonance(dip) and at_least(dip.depth_db, WEAK_DIP_MIN_DEPTH_DB)


def _with_band(sweep: Sweep, dip: Dip, runs: list[tuple[int, int]]) -> Resonance:
    return Resonance(
        index=dip.index,
        f_mhz=dip.f_mhz,
        s11_db=dip.s11_db,
        depth_db=dip.depth_db,
        band=_match_band(sweep, dip.index, runs),
    )


def _is_matched(s11_db: float) -> bool:
    return at_most(s11_db, MATCH_THRESHOLD_DB)


def _matched_runs(values: Sequence[float]) -> list[tuple[int, int]]:
    """For each point, the first and last index of the matched run it is in (itself if not)."""
    runs: list[tuple[int, int]] = []
    start = 0
    for i in range(len(values) + 1):
        if i == len(values) or not _is_matched(values[i]):
            runs.extend([(start, i - 1)] * (i - start))
            if i < len(values):
                runs.append((i, i))
            start = i + 1
    return runs


def _match_band(sweep: Sweep, index: int, runs: list[tuple[int, int]]) -> Band | None:
    if not _is_matched(sweep.s11_db[index]):
        return None
    first, last = runs[index]
    return Band(low_mhz=_band_edge(sweep, first, -1), high_mhz=_band_edge(sweep, last, 1))


def _band_edge(sweep: Sweep, inside: int, step: int) -> float:
    """Interpolate where S11 crosses the threshold just outside the matched run's end `inside`."""
    values, freqs = sweep.s11_db, sweep.f_mhz
    outside = inside + step
    if not 0 <= outside < len(values):
        return freqs[inside]
    fraction = (MATCH_THRESHOLD_DB - values[inside]) / (values[outside] - values[inside])
    return freqs[inside] + fraction * (freqs[outside] - freqs[inside])
