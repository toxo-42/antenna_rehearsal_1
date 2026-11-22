import math

import pytest

from src.impedance import impedance_at, low_freq_gamma_real
from src.models import Sweep


def make_sweep(gamma: list[complex] | None, count: int = 3) -> Sweep:
    size = len(gamma) if gamma is not None else count
    freqs = tuple(100.0 + i for i in range(size))
    return Sweep(f_mhz=freqs, s11_db=(-1.0,) * size, gamma=tuple(gamma) if gamma else None)


@pytest.mark.parametrize(
    ("gamma", "r_ohm", "x_ohm"),
    [
        (0j, 50.0, 0.0),
        (1 / 3 + 0j, 100.0, 0.0),
        (-1 / 3 + 0j, 25.0, 0.0),
        (1j, 0.0, 50.0),
        (-1j, 0.0, -50.0),
        (-1 + 0j, 0.0, 0.0),
    ],
)
def test_impedance_from_reflection_coefficient(gamma: complex, r_ohm: float, x_ohm: float) -> None:
    result = impedance_at(make_sweep([0j, gamma, 0j]), 1)

    assert result is not None
    assert result.r_ohm == pytest.approx(r_ohm, abs=1e-9)
    assert result.x_ohm == pytest.approx(x_ohm, abs=1e-9)


def test_total_reflection_in_phase_is_an_open_circuit() -> None:
    result = impedance_at(make_sweep([0j, 1 + 0j, 0j]), 1)

    assert result is not None
    assert math.isinf(result.r_ohm) and result.x_ohm == 0.0


def test_no_complex_data_gives_none() -> None:
    sweep = make_sweep(None)

    assert impedance_at(sweep, 1) is None
    assert low_freq_gamma_real(sweep) is None


def test_low_freq_gamma_real_averages_the_lowest_tenth_of_points() -> None:
    gamma = [0.9 + 0.3j, 0.7 - 0.1j] + [-0.5 + 0j] * 18  # 20 points -> lowest 2

    assert low_freq_gamma_real(make_sweep(gamma)) == pytest.approx(0.8)


def test_low_freq_gamma_real_uses_at_least_one_point() -> None:
    gamma = [-0.6 + 0.2j, 0.5 + 0j, 0.5 + 0j]

    assert low_freq_gamma_real(make_sweep(gamma)) == pytest.approx(-0.6)


def test_low_freq_point_count_rounds_down() -> None:
    gamma = [1 + 0j, 1 + 0j, -1 + 0j] + [0j] * 22  # 25 points -> lowest 2, not 3

    assert low_freq_gamma_real(make_sweep(gamma)) == pytest.approx(1.0)
