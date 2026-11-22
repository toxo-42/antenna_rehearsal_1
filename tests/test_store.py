"""SQLite storage: schema, bound values, one transaction per measurement, list order."""

import sqlite3
from pathlib import Path

import pytest

from src import store
from src.models import Sweep


def new_measurement(antenna_id: int, measured_at: str, stage: str = "good") -> store.NewMeasurement:
    sweep = Sweep(f_mhz=(400.0, 410.0, 420.0), s11_db=(-1.0, -20.0, -1.0))
    return store.NewMeasurement(
        antenna_id=antenna_id,
        measured_at=measured_at,
        source="synthetic",
        cal_mode="vna",
        stage=stage,
        resonance_mhz=410.0,
        s11_db=-20.0,
        bandwidth_pct=None,
        sweep_json=store.sweep_to_json(sweep),
        card_json="{}",
        change_note="",
    )


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "t.db"
    store.init_db(path)
    return path


def test_schema_has_tables_and_indexes(db: Path) -> None:
    with store.connect(db) as conn:
        antenna_cols = [r[1] for r in conn.execute("PRAGMA table_info(antennas)")]
        measurement_cols = [r[1] for r in conn.execute("PRAGMA table_info(measurements)")]
        indexes = [r[1] for r in conn.execute("PRAGMA index_list(measurements)")]
        indexed = {tuple(c[2] for c in conn.execute(f"PRAGMA index_info({n})")) for n in indexes}

    assert antenna_cols == ["id", "name", "kind", "target_mhz"]
    assert measurement_cols == [
        "id", "antenna_id", "measured_at", "source", "cal_mode", "stage", "resonance_mhz",
        "s11_db", "bandwidth_pct", "sweep_json", "card_json", "change_note",
    ]  # fmt: skip
    assert ("antenna_id", "measured_at") in indexed
    assert ("stage",) in indexed


def test_values_are_bound_not_spliced(db: Path) -> None:
    name = "x'); DROP TABLE antennas; --"
    with store.connect(db) as conn:
        antenna_id = store.insert_antenna(conn, name, "monopole", 433.0)
    with store.connect(db) as conn:
        assert store.get_antenna(conn, antenna_id) == {
            "id": antenna_id, "name": name, "kind": "monopole", "target_mhz": 433.0,
        }  # fmt: skip


def test_sweep_json_is_hz_db_re_im_with_null_without_complex_data() -> None:
    plain = Sweep(f_mhz=(1.5, 2.0), s11_db=(-1.0, -2.0))
    complex_sweep = Sweep(f_mhz=(1.5, 2.0), s11_db=(-1.0, -2.0), gamma=(0.5 + 0.25j, -1 + 0j))

    assert (
        store.sweep_to_json(plain)
        == "[[1500000.0, -1.0, null, null], [2000000.0, -2.0, null, null]]"
    )
    assert store.sweep_to_json(complex_sweep) == (
        "[[1500000.0, -1.0, 0.5, 0.25], [2000000.0, -2.0, -1.0, 0.0]]"
    )
    assert store.sweep_from_json(store.sweep_to_json(complex_sweep)) == complex_sweep
    assert store.sweep_from_json(store.sweep_to_json(plain)) == plain


def test_failed_transaction_leaves_nothing(db: Path) -> None:
    with pytest.raises(RuntimeError), store.connect(db) as conn:
        antenna_id = store.insert_antenna(conn, "a", "monopole", 433.0)
        store.insert_measurement(conn, new_measurement(antenna_id, "2026-11-22T10:00:00"))
        raise RuntimeError("fail after insert")

    with store.connect(db) as conn:
        assert store.list_antennas(conn) == []
        assert store.list_measurements(conn, store.MeasurementQuery()) == []


def test_measurement_needs_an_existing_antenna(db: Path) -> None:
    with pytest.raises(sqlite3.IntegrityError), store.connect(db) as conn:
        store.insert_measurement(conn, new_measurement(999, "2026-11-22T10:00:00"))


def test_list_is_newest_first_then_highest_id_and_drops_json_columns(db: Path) -> None:
    with store.connect(db) as conn:
        a = store.insert_antenna(conn, "a", "monopole", 433.0)
        b = store.insert_antenna(conn, "b", "patch", 433.0)
        first = store.insert_measurement(conn, new_measurement(a, "2026-11-22T10:00:00"))
        second = store.insert_measurement(conn, new_measurement(a, "2026-11-22T10:00:00", "none"))
        later = store.insert_measurement(conn, new_measurement(b, "2026-11-22T11:00:00"))

    with store.connect(db) as conn:
        rows = store.list_measurements(conn, store.MeasurementQuery())
        by_antenna = store.list_measurements(conn, store.MeasurementQuery(antenna_id=a))
        by_stage = store.list_measurements(conn, store.MeasurementQuery(stage="none"))
        paged = store.list_measurements(conn, store.MeasurementQuery(limit=1, offset=1))

    assert [r["id"] for r in rows] == [later, second, first]
    assert set(rows[0]) == {
        "id", "antenna_id", "measured_at", "source", "cal_mode", "stage", "resonance_mhz",
        "s11_db", "bandwidth_pct", "change_note",
    }  # fmt: skip
    assert [r["id"] for r in by_antenna] == [second, first]
    assert [r["id"] for r in by_stage] == [second]
    assert [r["id"] for r in paged] == [second]


def test_get_measurement_returns_all_columns_or_none(db: Path) -> None:
    with store.connect(db) as conn:
        a = store.insert_antenna(conn, "a", "monopole", 433.0)
        mid = store.insert_measurement(conn, new_measurement(a, "2026-11-22T10:00:00"))

    with store.connect(db) as conn:
        row = store.get_measurement(conn, mid)
        assert store.get_measurement(conn, mid + 1) is None
        assert store.get_antenna(conn, a + 1) is None

    assert row is not None
    assert row["sweep_json"].startswith("[[400000000.0, -1.0, null, null]")
    assert row["bandwidth_pct"] is None
