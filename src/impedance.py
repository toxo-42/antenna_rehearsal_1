"""Impedance from the complex reflection coefficient. Returns None when the sweep has no complex data."""

import math
from bisect import bisect_left

from src.models import LOW_FREQ_FRACTION, REFERENCE_OHM, Impedance, Sweep


def _impedance(gamma: complex) -> Impedance:
    if gamma == 1:
        return Impedance(r_ohm=math.inf, x_ohm=0.0)
    z = REFERENCE_OHM * (1 + gamma) / (1 - gamma)
    return Impedance(r_ohm=z.real, x_ohm=z.imag)


def impedance_at(sweep: Sweep, index: int) -> Impedance | None:
    """Z = 50 * (1 + g) / (1 - g) at one sweep point."""
    if sweep.gamma is None:
        return None
    return _impedance(sweep.gamma[index])


def reactance_at(sweep: Sweep, f_mhz: float) -> float | None:
    """X at a frequency inside the sweep; None outside it or when the value is not finite.

    On a measured point this is the measured X. Between two points it is linear interpolation.
    """
    freqs, gamma = sweep.f_mhz, sweep.gamma
    if gamma is None or not freqs or not freqs[0] <= f_mhz <= freqs[-1]:
        return None
    upper = bisect_left(freqs, f_mhz)
    x_ohm = _impedance(gamma[upper]).x_ohm
    if freqs[upper] != f_mhz:
        below = _impedance(gamma[upper - 1]).x_ohm
        fraction = (f_mhz - freqs[upper - 1]) / (freqs[upper] - freqs[upper - 1])
        x_ohm = below + fraction * (x_ohm - below)
    return x_ohm if math.isfinite(x_ohm) else None


def low_freq_gamma_real(sweep: Sweep) -> float | None:
    """Mean real part of the reflection coefficient over the lowest 10 % of points."""
    if sweep.gamma is None:
        return None
    count = max(1, int(len(sweep.gamma) * LOW_FREQ_FRACTION))
    return sum(g.real for g in sweep.gamma[:count]) / count
