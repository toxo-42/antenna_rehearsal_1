"""Demo mode never writes to its database; the demo export refuses bad paths in Korean."""

import sqlite3
import stat
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import create_app
from scripts import export_demo
from src import demo_export, store
from src.demo_export import ExportError, export_measurements

OLD_SCHEMA = store.SCHEMA.replace(",\n    length_cm REAL", "")
OLD_ROW = (
    "INSERT INTO measurements (antenna_id, measured_at, source, cal_mode, stage, sweep_json, "
    "card_json, change_note) VALUES (1, '2026-01-01T00:00:00', 'csv', 'vna', 'good', '[]', "
    "'{}', '')"
)


def filled(path: Path) -> Path:
    """One antenna with one synthetic measurement, saved in local mode."""
    client = TestClient(create_app(path))
    body = {"name": "a", "kind": "monopole", "target_mhz": 433.0}
    assert client.post("/api/antennas", json=body).status_code == 200
    sample = {"antenna_id": 1, "source": "synthetic", "sample": "good", "cal_mode": "vna"}
    assert client.post("/api/measurements", json=sample).status_code == 200
    return path


def old_schema_db(path: Path) -> Path:
    with sqlite3.connect(path) as conn:
        conn.executescript(OLD_SCHEMA)
        conn.execute("INSERT INTO antennas (name, kind, target_mhz) VALUES ('a', 'monopole', 433)")
        conn.execute(OLD_ROW)
    conn.close()
    return path


def test_an_old_schema_demo_db_stops_the_start_and_is_not_changed(tmp_path: Path) -> None:
    path = old_schema_db(tmp_path / "demo.db")
    before = path.read_bytes()

    with pytest.raises(ValueError, match=r"measurements\.length_cm") as caught:
        create_app(path, mode="demo")

    assert "시연용 DB" in str(caught.value)
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["demo.db"]


def test_a_demo_db_without_a_table_names_the_table(tmp_path: Path) -> None:
    path = tmp_path / "demo.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE antennas (id INTEGER PRIMARY KEY, name TEXT)")
    conn.close()

    with pytest.raises(ValueError) as caught:
        create_app(path, mode="demo")

    message = str(caught.value)
    assert "antennas.kind" in message and "antennas.target_mhz" in message
    assert "measurements 표" in message


def test_missing_schema_is_empty_for_a_current_database(tmp_path: Path) -> None:
    assert store.missing_schema(filled(tmp_path / "t.db")) == []


def test_a_read_only_file_is_served_in_demo_mode(tmp_path: Path) -> None:
    path = filled(tmp_path / "demo.db")
    path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    before = path.read_bytes()
    try:
        client = TestClient(create_app(path, mode="demo"))

        assert len(client.get("/api/measurements").json()) == 1
        assert client.get("/api/measurements/1").json()["card"]["stage"]
        assert client.get("/api/antennas/overview").json()[0]["measurement_count"] == 1
        assert path.read_bytes() == before
    finally:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def test_demo_connections_cannot_write(tmp_path: Path) -> None:
    path = filled(tmp_path / "demo.db")
    create_app(path, mode="demo")

    with pytest.raises(sqlite3.OperationalError), store.connect(path) as conn:
        store.insert_antenna(conn, "b", "patch", 2450.0)

    create_app(path)  # local mode on the same file writes again
    with store.connect(path) as conn:
        assert store.insert_antenna(conn, "b", "patch", 2450.0) == 2


def test_export_refuses_the_live_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = filled(tmp_path / "source.db")
    live = filled(tmp_path / "live" / "antenna.db") if (tmp_path / "live").mkdir() is None else None
    assert live is not None
    monkeypatch.setattr(demo_export, "LIVE_DB", live)
    before = live.read_bytes()
    (tmp_path / "sub").mkdir()

    for out in (live, tmp_path / "sub" / ".." / "live" / "antenna.db"):
        with pytest.raises(ExportError, match="실제 측정 DB"):
            export_measurements(source, out, [1])
    assert live.read_bytes() == before


def test_export_refuses_the_live_path_before_it_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = filled(tmp_path / "source.db")
    live = tmp_path / "antenna.db"
    monkeypatch.setattr(demo_export, "LIVE_DB", live)

    with pytest.raises(ExportError, match="실제 측정 DB"):
        export_measurements(source, tmp_path / "sub" / ".." / "antenna.db", [1])
    assert not live.exists()


def test_export_into_a_missing_folder_is_an_export_error(tmp_path: Path) -> None:
    source = filled(tmp_path / "source.db")

    with pytest.raises(ExportError, match="폴더가 없습니다"):
        export_measurements(source, tmp_path / "nowhere" / "demo.db", [1])
    assert not (tmp_path / "nowhere").exists()


@pytest.mark.parametrize("content", [b"", b"this is not a database, only some text\n" * 40])
def test_export_from_an_unreadable_source_is_an_export_error(
    content: bytes, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source, out = tmp_path / "source.db", tmp_path / "demo.db"
    source.write_bytes(content)

    with pytest.raises(ExportError, match="원본 DB를 읽을 수 없습니다"):
        export_measurements(source, out, [1])
    assert export_demo.main(["1", "--db", str(source), "--out", str(out)]) == 1
    assert export_demo.main(["--db", str(source), "--out", str(out)]) == 1
    assert "원본 DB를 읽을 수 없습니다" in capsys.readouterr().err
    assert not out.exists()
    assert source.read_bytes() == content
