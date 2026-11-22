import pytest

from src.models import Sweep
from src.resonance import find_resonances


def make_sweep(values: list[float], start: float = 100.0, step: float = 10.0) -> Sweep:
    freqs = tuple(start + step * i for i in range(len(values)))
    return Sweep(f_mhz=freqs, s11_db=tuple(values))


def test_single_dip_is_a_resonance_with_depth_from_lower_shoulder() -> None:
    scan = find_resonances(make_sweep([0, -1, -8, -2, -1]))

    assert len(scan.resonances) == 1
    found = scan.resonances[0]
    assert (found.index, found.f_mhz, found.s11_db) == (2, 120.0, -8)
    assert found.depth_db == pytest.approx(7.0)  # shoulders 0 and -1, lower one is -1
    assert scan.weak_dips == ()
    assert scan.minor_count == 0


def test_depth_stops_at_the_first_lower_point() -> None:
    scan = find_resonances(make_sweep([0, -5, -2, -9, -1]))

    assert [r.index for r in scan.resonances] == [3]
    assert scan.resonances[0].depth_db == pytest.approx(8.0)
    # -5 has depth 3 (right side stops at -9) but is shallower than -6 dB: weak dip only
    assert [(d.index, d.depth_db) for d in scan.weak_dips] == [(1, pytest.approx(3.0))]


def test_deep_enough_but_low_prominence_is_weak_or_minor() -> None:
    scan = find_resonances(make_sweep([-20, -22.5, -20, -21, -20, -30, -20]))

    assert [r.index for r in scan.resonances] == [5]
    assert [d.index for d in scan.weak_dips] == [1]  # depth 2.5
    assert scan.minor_count == 1  # depth 1.0 at index 3


def test_flat_plateau_and_endpoints_are_not_minima() -> None:
    assert find_resonances(make_sweep([-1, -1, -1, -1])).resonances == ()
    scan = find_resonances(make_sweep([-20, -1, 0, -1, -20]))
    assert scan.resonances == () and scan.weak_dips == () and scan.minor_count == 0


def test_plateau_minimum_is_counted_once_at_its_left_edge() -> None:
    scan = find_resonances(make_sweep([0, -8, -8, 0]))

    assert [r.index for r in scan.resonances] == [1]


def test_match_band_edges_are_linearly_interpolated() -> None:
    found = find_resonances(make_sweep([0, -5, -15, -5, 0])).resonances[0]

    assert found.band is not None
    assert found.band.low_mhz == pytest.approx(115.0)
    assert found.band.high_mhz == pytest.approx(125.0)
    assert found.bandwidth_pct == pytest.approx(10.0 / 120.0 * 100)


def test_resonance_shallower_than_match_threshold_has_no_band() -> None:
    found = find_resonances(make_sweep([0, -1, -8, -1, 0])).resonances[0]

    assert found.band is None
    assert found.bandwidth_pct is None


def test_band_is_clipped_at_the_sweep_edge() -> None:
    found = find_resonances(make_sweep([-12, -11, -20, -5, 0])).resonances[0]

    assert found.band is not None
    assert found.band.low_mhz == pytest.approx(100.0)
    assert found.band.high_mhz == pytest.approx(120.0 + 10.0 * 10 / 15)


def test_band_exactly_at_threshold_counts_as_matched() -> None:
    found = find_resonances(make_sweep([0, 0, -10, 0, 0])).resonances[0]

    assert found.band is not None
    assert found.band.low_mhz == pytest.approx(120.0)
    assert found.band.high_mhz == pytest.approx(120.0)


def test_thresholds_are_inclusive() -> None:
    assert len(find_resonances(make_sweep([0, -6, 0])).resonances) == 1  # exactly -6 dB
    assert len(find_resonances(make_sweep([-3, -6, -3])).resonances) == 1  # depth exactly 3
    weak = find_resonances(make_sweep([0, -2, 0]))
    assert len(weak.weak_dips) == 1 and weak.minor_count == 0  # depth exactly 2


def test_just_short_of_a_threshold_is_not_promoted() -> None:
    assert find_resonances(make_sweep([0, -5.99, 0])).resonances == ()
    assert find_resonances(make_sweep([-3.01, -6, -3.01])).resonances == ()
    assert find_resonances(make_sweep([0, -1.99, 0])).minor_count == 1


def test_inclusive_thresholds_survive_rounding_error() -> None:
    assert -3.1 - -6.1 < 3.0
    assert len(find_resonances(make_sweep([-3.1, -6.1, -3.1])).resonances) == 1
    assert -3.1 - -5.1 < 2.0
    assert len(find_resonances(make_sweep([-3.1, -5.1, -3.1])).weak_dips) == 1
