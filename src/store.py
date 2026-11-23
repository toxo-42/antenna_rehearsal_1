"""SQLite storage for antennas and measurements. Every value is bound with `?`."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import astuple, dataclass, fields
from pathlib import Path
from typing import Any

from src.models import Sweep

HZ_PER_MHZ = 1_000_000.0
SQLITE_MAX_INT = 2**63 - 1  # SQLite integers are signed 64-bit; a larger id can never exist
Row = dict[str, Any]

SCHEMA = """
CREATE TABLE IF NOT EXISTS antennas (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    target_mhz REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY,
    antenna_id INTEGER NOT NULL REFERENCES antennas(id),
    measured_at TEXT NOT NULL,
    source TEXT NOT NULL,
    cal_mode TEXT NOT NULL,
    stage TEXT NOT NULL,
    resonance_mhz REAL,
    s11_db REAL,
    bandwidth_pct REAL,
    sweep_json TEXT NOT NULL,
    card_json TEXT NOT NULL,
    change_note TEXT NOT NULL,
    length_cm REAL
);
CREATE INDEX IF NOT EXISTS measurements_antenna_time ON measurements (antenna_id, measured_at);
CREATE INDEX IF NOT EXISTS measurements_stage ON measurements (stage);
"""

LIST_COLUMNS = (
    "id, antenna_id, measured_at, source, cal_mode, stage, "
    "resonance_mhz, s11_db, bandwidth_pct, change_note, length_cm"
)
# Columns added after the first release: a database made before them gets them on start.
ADDED_COLUMNS = {"length_cm": "REAL"}


@dataclass(frozen=True)
class NewMeasurement:
    """One row for `measurements`, in column order, without the id."""

    antenna_id: int
    measured_at: str
    source: str
    cal_mode: str
    stage: str
    resonance_mhz: float | None
    s11_db: float | None
    bandwidth_pct: float | None
    sweep_json: str
    card_json: str
    change_note: str
    length_cm: float | None = None


@dataclass(frozen=True)
class MeasurementQuery:
    antenna_id: int | None = None
    stage: str | None = None
    limit: int = 50
    offset: int = 0


def init_db(db_path: Path) -> None:
    """Create the tables and indexes if they are missing, and add the newer columns."""
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        have = {row["name"] for row in conn.execute("PRAGMA table_info(measurements)")}
        for name, kind in ADDED_COLUMNS.items():
            if name not in have:
                conn.execute(f"ALTER TABLE measurements ADD COLUMN {name} {kind}")


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    """Open one connection, commit on success, roll back on error, and always close."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_antenna(conn: sqlite3.Connection, name: str, kind: str, target_mhz: float) -> int:
    sql = "INSERT INTO antennas (name, kind, target_mhz) VALUES (?, ?, ?)"
    return _last_id(conn.execute(sql, (name, kind, target_mhz)))


def fits_sqlite(value: int) -> bool:
    """Whether SQLite can bind the integer; binding a larger one raises OverflowError."""
    return -SQLITE_MAX_INT - 1 <= value <= SQLITE_MAX_INT


def get_antenna(conn: sqlite3.Connection, antenna_id: int) -> Row | None:
    if not fits_sqlite(antenna_id):
        return None
    row = conn.execute("SELECT * FROM antennas WHERE id = ?", (antenna_id,)).fetchone()
    return dict(row) if row is not None else None


def list_antennas(conn: sqlite3.Connection) -> list[Row]:
    return [dict(row) for row in conn.execute("SELECT * FROM antennas ORDER BY id")]


def insert_measurement(conn: sqlite3.Connection, new: NewMeasurement) -> int:
    names = [field.name for field in fields(new)]
    marks = ", ".join("?" for _ in names)
    sql = f"INSERT INTO measurements ({', '.join(names)}) VALUES ({marks})"
    return _last_id(conn.execute(sql, astuple(new)))


def get_measurement(conn: sqlite3.Connection, measurement_id: int) -> Row | None:
    if not fits_sqlite(measurement_id):
        return None
    sql = "SELECT * FROM measurements WHERE id = ?"
    row = conn.execute(sql, (measurement_id,)).fetchone()
    return dict(row) if row is not None else None


def list_measurements(conn: sqlite3.Connection, query: MeasurementQuery) -> list[Row]:
    """Newest first, then highest id first. Filters are optional."""
    if query.antenna_id is not None and not fits_sqlite(query.antenna_id):
        return []
    sql = (
        f"SELECT {LIST_COLUMNS} FROM measurements "
        "WHERE (? IS NULL OR antenna_id = ?) AND (? IS NULL OR stage = ?) "
        "ORDER BY measured_at DESC, id DESC LIMIT ? OFFSET ?"
    )
    params = (query.antenna_id, query.antenna_id, query.stage, query.stage)
    rows = conn.execute(sql, (*params, query.limit, query.offset))
    return [dict(row) for row in rows]


def count_measurements(db_path: Path) -> int:
    """0 when the file has no measurements table (e.g. an empty file). Creates nothing."""
    with connect(db_path) as conn:
        sql = "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'measurements'"
        if conn.execute(sql).fetchone() is None:
            return 0
        return conn.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]


def sweep_to_json(sweep: Sweep) -> str:
    """`[f_hz, s11_db, re, im]` per point; re and im are null without complex data."""
    gamma = sweep.gamma or (None,) * len(sweep.f_mhz)
    points = [
        [f_mhz * HZ_PER_MHZ, s11_db, *((g.real, g.imag) if g is not None else (None, None))]
        for f_mhz, s11_db, g in zip(sweep.f_mhz, sweep.s11_db, gamma, strict=True)
    ]
    return json.dumps(points)


def sweep_from_json(text: str) -> Sweep:
    points = json.loads(text)
    has_complex = bool(points) and all(p[2] is not None and p[3] is not None for p in points)
    return Sweep(
        f_mhz=tuple(p[0] / HZ_PER_MHZ for p in points),
        s11_db=tuple(p[1] for p in points),
        gamma=tuple(complex(p[2], p[3]) for p in points) if has_complex else None,
    )


def _last_id(cursor: sqlite3.Cursor) -> int:
    if cursor.lastrowid is None:
        raise sqlite3.DatabaseError("삽입한 행의 id를 받지 못했습니다.")
    return cursor.lastrowid
