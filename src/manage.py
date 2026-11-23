"""The manage page: what is stored per antenna, renaming, and deleting. Deleting cannot be
undone, so the screen asks first; here every call does exactly one thing in one transaction."""

import sqlite3
from pathlib import Path

from src import store
from src.service import InputError, NotFoundError, Row, json_safe


def overview(db_path: Path) -> list[Row]:
    """Every antenna with its measurement count and the stage and resonance of the newest one."""
    with store.connect(db_path) as conn:
        return json_safe([_overview_row(conn, antenna) for antenna in store.list_antennas(conn)])


def _overview_row(conn: sqlite3.Connection, antenna: Row) -> Row:
    newest = store.list_measurements(conn, store.MeasurementQuery(antenna["id"], limit=1))
    last = newest[0] if newest else None
    return {
        **antenna,
        "measurement_count": store.count_for_antenna(conn, antenna["id"]),
        "last_measured_at": last["measured_at"] if last else None,
        "last_stage": last["stage"] if last else None,
        "last_resonance_mhz": last["resonance_mhz"] if last else None,
    }


def rename_antenna(db_path: Path, antenna_id: int, name: str) -> Row:
    """Change the name only. The kind and the target decide the verdicts already stored."""
    if not name.strip():
        raise InputError("안테나 이름을 입력해 주세요.")
    with store.connect(db_path) as conn:
        if not store.rename_antenna(conn, antenna_id, name):
            raise NotFoundError(f"안테나 {antenna_id}번이 없습니다.")
        antenna = store.get_antenna(conn, antenna_id)
    return json_safe(antenna)


def delete_measurement(db_path: Path, measurement_id: int) -> None:
    with store.connect(db_path) as conn:
        if not store.delete_measurement(conn, measurement_id):
            raise NotFoundError(f"측정 {measurement_id}번이 없습니다.")


def delete_antenna(db_path: Path, antenna_id: int) -> Row:
    """Delete the antenna and all of its measurements; reports how many measurements went."""
    with store.connect(db_path) as conn:
        gone = store.delete_antenna(conn, antenna_id)
    if gone is None:
        raise NotFoundError(f"안테나 {antenna_id}번이 없습니다.")
    return {"deleted_measurements": gone}
