"""Sweep builders and shortcuts shared by the diagnosis and card tests."""

import math
from collections.abc import Sequence

from src.diagnosis import context_for, diagnose
from src.models import Antenna, AntennaKind, CalMode, Diagnosis, RuleContext, Sweep

REFERENCE_OHM = 50.0


def antenna(target: float, kind: AntennaKind = AntennaKind.MONOPOLE) -> Antenna:
    return Antenna(name="t", kind=kind, target_mhz=target)


def magnitude_sweep(values: Sequence[float], start: float = 400.0, step: float = 10.0) -> Sweep:
    """A sweep with S11 magnitudes only (no complex data)."""
    freqs = tuple(start + step * i for i in range(len(values)))
    return Sweep(f_mhz=freqs, s11_db=tuple(float(v) for v in values))


def gamma_sweep(freqs: Sequence[float], gamma: Sequence[complex]) -> Sweep:
    s11_db = tuple(20 * math.log10(abs(g)) for g in gamma)
    return Sweep(f_mhz=tuple(freqs), s11_db=s11_db, gamma=tuple(gamma))


def impedance_sweep(freqs: Sequence[float], impedances: Sequence[complex]) -> Sweep:
    """A sweep whose reflection coefficient comes from the given impedance at each point."""
    gamma = [(z - REFERENCE_OHM) / (z + REFERENCE_OHM) for z in impedances]
    return gamma_sweep(freqs, gamma)


def dip_sweep(dips: dict[float, float], start: float, stop: float, step: float = 10.0) -> Sweep:
    """0 dB everywhere except single-point dips at the given frequencies."""
    count = round((stop - start) / step) + 1
    freqs = tuple(start + step * i for i in range(count))
    return Sweep(f_mhz=freqs, s11_db=tuple(dips.get(f, 0.0) for f in freqs))


def context(sweep: Sweep, ant: Antenna, cal_mode: CalMode = CalMode.VNA) -> RuleContext:
    return context_for(sweep, ant, cal_mode)


def keys(sweep: Sweep, ant: Antenna, cal_mode: CalMode = CalMode.VNA) -> list[str]:
    return [d.key for d in diagnose(context(sweep, ant, cal_mode))]


def find(sweep: Sweep, ant: Antenna, key: str) -> Diagnosis:
    """The diagnosis with this key; fails the test when it is absent."""
    found = [d for d in diagnose(context(sweep, ant)) if d.key == key]
    assert len(found) == 1, f"{key} not found"
    return found[0]
