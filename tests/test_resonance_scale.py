"""The resonance scan stays linear on long sweeps and gives the same answer as the plain walk."""

import random
import time
from collections.abc import Sequence

import pytest

from src.models import MATCH_THRESHOLD_DB, Sweep
from src.resonance import find_resonances


def reference_depths(values: Sequence[float]) -> dict[int, float]:
    """The original definition: walk out from each minimum until a lower point or the end."""

    def shoulder(index: int, step: int) -> float:
        peak, j = values[index], index + step
        while 0 <= j < len(values) and values[j] >= values[index]:
            peak, j = max(peak, values[j]), j + step
        return peak

    minima = [
        i
        for i in range(1, len(values) - 1)
        if values[i] < values[i - 1] and values[i] <= values[i + 1]
    ]
    return {i: min(shoulder(i, -1), shoulder(i, 1)) - values[i] for i in minima}


def reference_band(
    values: Sequence[float], freqs: Sequence[float], index: int
) -> tuple[float, ...]:
    def edge(step: int) -> float:
        inside = index
        while 0 <= inside + step < len(values) and values[inside + step] <= MATCH_THRESHOLD_DB:
            inside += step
        outside = inside + step
        if not 0 <= outside < len(values):
            return freqs[inside]
        fraction = (MATCH_THRESHOLD_DB - values[inside]) / (values[outside] - values[inside])
        return freqs[inside] + fraction * (freqs[outside] - freqs[inside])

    return (edge(-1), edge(1))


@pytest.mark.parametrize("seed", range(200))
def test_scan_matches_the_plain_walk(seed: int) -> None:
    rng = random.Random(seed)
    levels = [0.0, -1.0, -3.0, -6.0, -9.0, -10.0, -11.0, -15.0, -20.0, -30.0]
    values = [rng.choice(levels) + rng.choice([0.0, 0.0, 0.5]) for _ in range(rng.randint(3, 40))]
    freqs = tuple(100.0 + 7.0 * i for i in range(len(values)))

    scan = find_resonances(Sweep(f_mhz=freqs, s11_db=tuple(values)))
    dips = [*scan.resonances, *scan.weak_dips]
    expected = reference_depths(values)

    assert {d.index: d.depth_db for d in dips} == {
        i: depth for i, depth in expected.items() if i in {d.index for d in dips}
    }
    assert len(dips) + scan.minor_count == len(expected)
    for found in scan.resonances:
        if found.band is not None:
            band = (found.band.low_mhz, found.band.high_mhz)
            assert band == reference_band(values, freqs, found.index)


@pytest.mark.parametrize("pair", [(-1.0, -5.0), (-11.0, -15.0)])
def test_many_dips_scan_in_linear_time(pair: tuple[float, float]) -> None:
    n = 60_000
    values = tuple(pair[i % 2] for i in range(n))
    sweep = Sweep(f_mhz=tuple(100.0 + 0.001 * i for i in range(n)), s11_db=values)

    started = time.perf_counter()
    scan = find_resonances(sweep)
    elapsed = time.perf_counter() - started

    assert len(scan.resonances) + len(scan.weak_dips) + scan.minor_count == n // 2 - 1
    assert elapsed < 2.0
