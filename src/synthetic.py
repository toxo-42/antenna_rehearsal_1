"""Synthetic S11 sweeps for running without an instrument. Always label these as synthetic data."""

import math
from collections.abc import Callable
from dataclasses import dataclass

from src.models import REFERENCE_OHM, Antenna, AntennaKind, Sweep

GammaFn = Callable[[float], complex]

START_MHZ = 10.0
STOP_MHZ = 1000.0
POINTS = 201
PATCH_PREFIX = "patch_"
MIN_MAGNITUDE = 1e-12


@dataclass(frozen=True)
class Sample:
    antenna: Antenna
    sweep: Sweep


def rlc(f0_mhz: float, r_ohm: float, q: float) -> GammaFn:
    """Series RLC: Z = R + j*R*Q*(f/f0 - f0/f), g = (Z - 50) / (Z + 50)."""

    def gamma(f_mhz: float) -> complex:
        z = complex(r_ohm, r_ohm * q * (f_mhz / f0_mhz - f0_mhz / f_mhz))
        return (z - REFERENCE_OHM) / (z + REFERENCE_OHM)

    return gamma


def constant(value: complex) -> GammaFn:
    return lambda f_mhz: complex(value)


def product(first: GammaFn, second: GammaFn) -> GammaFn:
    return lambda f_mhz: first(f_mhz) * second(f_mhz)


# name -> (target MHz, reflection coefficient). Names starting with "patch_" are patch antennas.
_SPECS: dict[str, tuple[float, GammaFn]] = {
    "good": (433.0, rlc(433.0, 45.0, 5.0)),
    "offtarget_low": (433.0, rlc(380.0, 45.0, 5.0)),
    "offtarget_high": (433.0, rlc(480.0, 45.0, 5.0)),
    "narrow": (433.0, rlc(433.0, 45.0, 15.0)),
    "unmatched_low_r": (433.0, rlc(433.0, 20.0, 8.0)),
    "unmatched_high_r": (433.0, rlc(433.0, 120.0, 5.0)),
    "far_low": (433.0, rlc(277.3, 45.0, 8.0)),
    "far_high": (433.0, rlc(700.0, 45.0, 8.0)),
    "open": (433.0, constant(0.99)),
    "short": (433.0, constant(-0.99)),
    "lossy": (433.0, constant(0.5)),
    "positive": (433.0, constant(1.05)),
    "two_res": (650.0, product(rlc(277.3, 45.0, 8.0), rlc(881.2, 45.0, 8.0))),
    "third_mode": (433.0, product(rlc(144.0, 45.0, 8.0), rlc(433.0, 22.0, 10.0))),
    "patch_good": (433.0, rlc(433.0, 45.0, 15.0)),
    "patch_narrow": (433.0, rlc(433.0, 45.0, 40.0)),
    "patch_low_r": (433.0, rlc(433.0, 20.0, 15.0)),
    "patch_high_r": (433.0, rlc(433.0, 120.0, 15.0)),
}

SAMPLE_NAMES: tuple[str, ...] = tuple(_SPECS)


def make_sample(name: str) -> Sample:
    """Build one named sample. Raises KeyError for an unknown name."""
    target_mhz, gamma_fn = _SPECS[name]
    kind = AntennaKind.PATCH if name.startswith(PATCH_PREFIX) else AntennaKind.MONOPOLE
    freqs = tuple(START_MHZ + (STOP_MHZ - START_MHZ) * i / (POINTS - 1) for i in range(POINTS))
    gamma = tuple(gamma_fn(f) for f in freqs)
    s11_db = tuple(20 * math.log10(max(abs(g), MIN_MAGNITUDE)) for g in gamma)
    return Sample(
        antenna=Antenna(name=name, kind=kind, target_mhz=target_mhz),
        sweep=Sweep(f_mhz=freqs, s11_db=s11_db, gamma=gamma),
    )
