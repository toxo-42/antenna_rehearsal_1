"""Impedance from the complex reflection coefficient. Returns None when the sweep has no complex data."""

import math

from src.models import LOW_FREQ_FRACTION, REFERENCE_OHM, Impedance, Sweep


def impedance_at(sweep: Sweep, index: int) -> Impedance | None:
    """Z = 50 * (1 + g) / (1 - g) at one sweep point."""
    if sweep.gamma is None:
        return None
    gamma = sweep.gamma[index]
    if gamma == 1:
        return Impedance(r_ohm=math.inf, x_ohm=0.0)
    z = REFERENCE_OHM * (1 + gamma) / (1 - gamma)
    return Impedance(r_ohm=z.real, x_ohm=z.imag)


def low_freq_gamma_real(sweep: Sweep) -> float | None:
    """Mean real part of the reflection coefficient over the lowest 10 % of points."""
    if sweep.gamma is None:
        return None
    count = max(1, int(len(sweep.gamma) * LOW_FREQ_FRACTION))
    return sum(g.real for g in sweep.gamma[:count]) / count
