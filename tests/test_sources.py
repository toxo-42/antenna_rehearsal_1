"""Sweep sources: synthetic samples and sweeps read back from stored measurements."""

from pathlib import Path

import pytest

from src import store
from src.models import Sweep
from src.sources import StoredSource, SweepSource, SyntheticSource
from src.synthetic import make_sample


def test_synthetic_source_returns_the_sample_sweep() -> None:
    source: SweepSource = SyntheticSource("good")

    assert source.source == "synthetic"
    assert source.read() == make_sample("good").sweep


def test_synthetic_source_rejects_an_unknown_name() -> None:
    with pytest.raises(KeyError):
        SyntheticSource("nope")


def test_stored_source_returns_the_saved_sweep(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    store.init_db(db)
    sweep = Sweep(f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, -20.0, -1.0), gamma=(0j, 1j, -1j))
    with store.connect(db) as conn:
        antenna_id = store.insert_antenna(conn, "a", "monopole", 410.0)
        mid = store.insert_measurement(
            conn,
            store.NewMeasurement(
                antenna_id=antenna_id, measured_at="2026-11-22T10:00:00", source="csv",
                cal_mode="vna", stage="good", resonance_mhz=410.0, s11_db=-20.0,
                bandwidth_pct=None, sweep_json=store.sweep_to_json(sweep), card_json="{}",
                change_note="",
            ),
        )  # fmt: skip

    source: SweepSource = StoredSource(db, mid)

    assert source.source == "stored"
    assert source.read() == sweep
    with pytest.raises(LookupError):
        StoredSource(db, mid + 1).read()
