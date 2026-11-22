"""Service rules that do not need HTTP: one sweep check for every source, JSON-safe output."""

import math
from dataclasses import dataclass
from pathlib import Path

import pytest

from src import service, store
from src.models import Sweep
from src.sweep_parser import check_sweep, parse_sweep_csv


@dataclass
class FixedSource:
    """A source that returns whatever sweep it was given, like a misbehaving instrument."""

    sweep: Sweep
    source: str = "usb"

    def read(self) -> Sweep:
        return self.sweep


BAD_SWEEPS = {
    "two_points": Sweep(f_mhz=(400.0, 410.0), s11_db=(-1.0, -20.0)),
    "descending": Sweep(f_mhz=(420.0, 410.0, 400.0), s11_db=(-1.0, -20.0, -1.0)),
    "repeated": Sweep(f_mhz=(400.0, 400.0, 420.0), s11_db=(-1.0, -20.0, -1.0)),
    "nan_db": Sweep(f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, math.nan, -1.0)),
    "inf_freq": Sweep(f_mhz=(400.0, 410.0, math.inf), s11_db=(-1.0, -20.0, -1.0)),
    "nan_gamma": Sweep(
        f_mhz=(400.0, 410.0, 420.0),
        s11_db=(-1.0, -20.0, -1.0),
        gamma=(0j, complex(math.nan, 0.0), 0j),
    ),
    "length_mismatch": Sweep(f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, -20.0)),
    "empty_gamma": Sweep(f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, -20.0, -1.0), gamma=()),
    "zero_freq": Sweep(f_mhz=(-10.0, 0.0, 420.0), s11_db=(-1.0, -20.0, -1.0)),
    "huge_freq": Sweep(f_mhz=(400.0, 410.0, 2e6), s11_db=(-1.0, -20.0, -1.0)),
    "huge_db": Sweep(f_mhz=(400.0, 410.0, 420.0), s11_db=(1e308, -1e308, -1.0)),
    "huge_gamma": Sweep(
        f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, -20.0, -1.0), gamma=(0j, 2000j, 0j)
    ),
}


@pytest.mark.parametrize("name", list(BAD_SWEEPS))
def test_check_sweep_rejects_a_bad_sweep(name: str) -> None:
    with pytest.raises(ValueError):
        check_sweep(BAD_SWEEPS[name])


# The same bad sweep written as CSV rows (f_hz, s11_db, re, im) for the parser.
CSV_TWINS = {
    "two_points": [("400e6", "-1", "0", "0"), ("410e6", "-20", "0", "0")],
    "descending": [("420e6", "-1", "0", "0"), ("410e6", "-20", "0", "0"), ("400e6", "-1", "0", "0")],
    "repeated": [("400e6", "-1", "0", "0"), ("400e6", "-20", "0", "0"), ("420e6", "-1", "0", "0")],
    "nan_db": [("400e6", "-1", "0", "0"), ("410e6", "nan", "0", "0"), ("420e6", "-1", "0", "0")],
    "inf_freq": [("400e6", "-1", "0", "0"), ("410e6", "-20", "0", "0"), ("inf", "-1", "0", "0")],
    "nan_gamma": [("400e6", "-1", "0", "0"), ("410e6", "-20", "nan", "0"), ("420e6", "-1", "0", "0")],
    "zero_freq": [("-10e6", "-1", "0", "0"), ("0", "-20", "0", "0"), ("420e6", "-1", "0", "0")],
    "huge_freq": [("400e6", "-1", "0", "0"), ("410e6", "-20", "0", "0"), ("2e12", "-1", "0", "0")],
    "huge_db": [("400e6", "1e308", "0", "0"), ("410e6", "-1e308", "0", "0"), ("420e6", "-1", "0", "0")],
    "huge_gamma": [("400e6", "-1", "0", "0"), ("410e6", "-20", "0", "2000"), ("420e6", "-1", "0", "0")],
    "valid": [("400e6", "-1", "0", "0"), ("410e6", "-20", "0", "0"), ("420e6", "-1", "0", "0")],
}  # fmt: skip


def csv_of(rows: list[tuple[str, str, str, str]]) -> str:
    return "Frequency_Hz,S11_dB,S11_real,S11_imag\n" + "".join(",".join(r) + "\n" for r in rows)


@pytest.mark.parametrize("name", list(CSV_TWINS))
def test_check_sweep_agrees_with_the_csv_parser(name: str) -> None:
    sweep = BAD_SWEEPS.get(name) or Sweep(
        f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, -20.0, -1.0), gamma=(0j,) * 3
    )

    def verdict(check: object, value: object) -> bool:
        try:
            check(value)  # type: ignore[operator]
        except ValueError:
            return False
        return True

    assert verdict(check_sweep, sweep) == verdict(parse_sweep_csv, csv_of(CSV_TWINS[name]))


def test_check_sweep_accepts_a_valid_sweep() -> None:
    check_sweep(Sweep(f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, -20.0, -1.0), gamma=(0j,) * 3))


@pytest.fixture
def db_with_antenna(tmp_path: Path) -> tuple[Path, int]:
    db = tmp_path / "t.db"
    store.init_db(db)
    antenna = service.create_antenna(db, service.AntennaInput("a", "monopole", 410.0))
    return db, antenna["id"]


@pytest.mark.parametrize("name", list(BAD_SWEEPS))
def test_any_source_goes_through_the_sweep_check(
    db_with_antenna: tuple[Path, int], name: str
) -> None:
    db, antenna_id = db_with_antenna
    request = service.MeasureInput(antenna_id=antenna_id, cal_mode="vna", change_note="")

    with pytest.raises(service.InputError):
        service.measure(db, FixedSource(BAD_SWEEPS[name]), request)

    assert service.list_measurements(db, service.ListInput()) == []


def test_json_safe_turns_non_finite_numbers_into_null() -> None:
    value = {"a": math.nan, "b": [math.inf, -math.inf, 1.5, 2], "c": "inf", "d": None}

    assert service.json_safe(value) == {"a": None, "b": [None, None, 1.5, 2], "c": "inf", "d": None}
