import math

import pytest

from src.impedance import impedance_at, low_freq_gamma_real, reactance_at
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


def reactance_sweep(reactances: list[float]) -> Sweep:
    """Points at 100, 110, ... MHz with impedance 50 + jX."""
    gamma = [complex(0, x) / complex(100, x) for x in reactances]
    freqs = tuple(100.0 + 10.0 * i for i in range(len(gamma)))
    return Sweep(f_mhz=freqs, s11_db=(-1.0,) * len(gamma), gamma=tuple(gamma))


@pytest.mark.parametrize(
    ("f_mhz", "x_ohm"),
    [(100.0, -40.0), (105.0, -10.0), (110.0, 20.0), (112.5, 30.0), (120.0, 60.0)],
)
def test_reactance_at_interpolates_between_the_surrounding_points(
    f_mhz: float, x_ohm: float
) -> None:
    sweep = reactance_sweep([-40.0, 20.0, 60.0])

    assert reactance_at(sweep, f_mhz) == pytest.approx(x_ohm, abs=1e-9)


@pytest.mark.parametrize("f_mhz", [99.9, 120.1])
def test_reactance_at_is_none_outside_the_sweep(f_mhz: float) -> None:
    assert reactance_at(reactance_sweep([-40.0, 20.0, 60.0]), f_mhz) is None


def test_reactance_at_a_measured_point_is_the_measured_value() -> None:
    sweep = reactance_sweep([1e18, 40.0, 60.0])  # interpolating from 1e18 would cancel the 40

    assert reactance_at(sweep, 110.0) == pytest.approx(40.0, abs=1e-9)


@pytest.mark.parametrize("f_mhz", [100.0, 105.0, 110.0, 115.0])
def test_reactance_at_is_none_when_the_result_is_not_finite(f_mhz: float) -> None:
    near_open = 1 + 1e-310j  # not exactly 1, so the impedance overflows
    sweep = make_sweep([0.5 + 0.5j, near_open, 0.5 - 0.5j])
    sweep = Sweep(f_mhz=(100.0, 110.0, 120.0), s11_db=sweep.s11_db, gamma=sweep.gamma)

    expected_finite = f_mhz == 100.0
    assert (reactance_at(sweep, f_mhz) is not None) == expected_finite


def test_reactance_at_is_none_without_complex_data() -> None:
    assert reactance_at(make_sweep(None), 101.0) is None
