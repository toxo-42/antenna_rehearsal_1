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
    dips = [
        Dip(index=i, f_mhz=sweep.f_mhz[i], s11_db=values[i], depth_db=_depth(values, i))
        for i in _local_minima(values)
    ]
    resonances = tuple(_with_band(sweep, dip) for dip in dips if _is_resonance(dip))
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


def _shoulder(values: Sequence[float], index: int, step: int) -> float:
    """Highest value on one side before a point lower than the dip (or the sweep end)."""
    peak = values[index]
    j = index + step
    while 0 <= j < len(values) and values[j] >= values[index]:
        peak = max(peak, values[j])
        j += step
    return peak


def _depth(values: Sequence[float], index: int) -> float:
    lower_shoulder = min(_shoulder(values, index, -1), _shoulder(values, index, 1))
    return lower_shoulder - values[index]


def _is_resonance(dip: Dip) -> bool:
    deep_enough = at_least(dip.depth_db, RESONANCE_MIN_DEPTH_DB)
    return deep_enough and at_most(dip.s11_db, RESONANCE_MAX_S11_DB)


def _is_weak_dip(dip: Dip) -> bool:
    return not _is_resonance(dip) and at_least(dip.depth_db, WEAK_DIP_MIN_DEPTH_DB)


def _with_band(sweep: Sweep, dip: Dip) -> Resonance:
    return Resonance(
        index=dip.index,
        f_mhz=dip.f_mhz,
        s11_db=dip.s11_db,
        depth_db=dip.depth_db,
        band=_match_band(sweep, dip.index),
    )


def _is_matched(s11_db: float) -> bool:
    return at_most(s11_db, MATCH_THRESHOLD_DB)


def _match_band(sweep: Sweep, index: int) -> Band | None:
    if not _is_matched(sweep.s11_db[index]):
        return None
    return Band(low_mhz=_band_edge(sweep, index, -1), high_mhz=_band_edge(sweep, index, 1))


def _band_edge(sweep: Sweep, index: int, step: int) -> float:
    """Walk outward while matched; interpolate where S11 crosses the threshold."""
    values, freqs = sweep.s11_db, sweep.f_mhz
    inside = index
    while 0 <= inside + step < len(values) and _is_matched(values[inside + step]):
        inside += step
    outside = inside + step
    if not 0 <= outside < len(values):
        return freqs[inside]
    fraction = (MATCH_THRESHOLD_DB - values[inside]) / (values[outside] - values[inside])
    return freqs[inside] + fraction * (freqs[outside] - freqs[inside])
