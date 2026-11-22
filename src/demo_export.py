"""Copy chosen measurements, with their antennas, into a fresh database for demo mode.

Ids are kept, so a measurement has the same id in both databases.
"""

import os
import sqlite3
import tempfile
from collections.abc import Sequence
from pathlib import Path

from src import store

Row = store.Row


class ExportError(ValueError):
    """The choice or the paths cannot make a demo database. Nothing was written."""


def export_measurements(source: Path, out: Path, ids: Sequence[int]) -> int:
    """Write `out` with only the measurements `ids` and their antennas; returns the count.

    An older `out` is replaced only after the new one is complete.
    """
    chosen = _checked_ids(ids)
    if not source.is_file():
        raise ExportError(f"원본 DB가 없습니다: {source}")
    # samefile also sees through hard links and letter case on case-insensitive disks.
    if out.exists() and out.samefile(source):
        raise ExportError(f"내보낼 파일이 원본 DB와 같습니다: {out}")
    with store.connect(source) as conn:
        measurements = _chosen_measurements(conn, chosen)
        antenna_ids = {row["antenna_id"] for row in measurements}
        antennas = [row for row in store.list_antennas(conn) if row["id"] in antenna_ids]
    _write(out, antennas, measurements)
    return len(measurements)


def _checked_ids(ids: Sequence[int]) -> list[int]:
    if not ids:
        raise ExportError("내보낼 측정 id를 하나 이상 고르세요.")
    out_of_range = [i for i in ids if not store.fits_sqlite(i)]
    if out_of_range:
        raise ExportError(f"측정 id가 저장할 수 있는 범위를 벗어났습니다: {out_of_range}")
    repeated = sorted({i for i in ids if list(ids).count(i) > 1})
    if repeated:
        raise ExportError(f"같은 측정 id가 두 번 이상 있습니다: {repeated}")
    return sorted(ids)


def _chosen_measurements(conn: sqlite3.Connection, ids: list[int]) -> list[Row]:
    marks = ", ".join("?" for _ in ids)
    sql = f"SELECT * FROM measurements WHERE id IN ({marks}) ORDER BY id"
    rows = [dict(row) for row in conn.execute(sql, ids)]
    missing = sorted(set(ids) - {row["id"] for row in rows})
    if missing:
        raise ExportError(f"원본 DB에 없는 측정 id: {missing}")
    return rows


def _write(out: Path, antennas: list[Row], measurements: list[Row]) -> None:
    """Build in a new temporary file next to `out`; only that file is ever removed."""
    handle, name = tempfile.mkstemp(dir=out.parent, prefix=f"{out.name}.", suffix=".part")
    os.close(handle)
    partial = Path(name)
    try:
        store.init_db(partial)
        with store.connect(partial) as conn:
            _insert_rows(conn, "antennas", antennas)
            _insert_rows(conn, "measurements", measurements)
        partial.replace(out)
    finally:
        partial.unlink(missing_ok=True)


def _insert_rows(conn: sqlite3.Connection, table: str, rows: list[Row]) -> None:
    """`table` is one of this module's two names; values are bound with `?`."""
    for row in rows:
        names = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        conn.execute(f"INSERT INTO {table} ({names}) VALUES ({marks})", tuple(row.values()))
