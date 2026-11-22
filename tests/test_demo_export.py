"""Copying chosen measurements, and only their antennas, into a fresh demo database."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import create_app
from scripts import export_demo
from src.demo_export import ExportError, export_measurements


@pytest.fixture
def source(tmp_path: Path) -> Path:
    """Antennas 1 and 2; measurements 1, 2 on antenna 1 and 3 on antenna 2."""
    path = tmp_path / "antenna.db"
    client = TestClient(create_app(path))
    for name, kind in (("m", "monopole"), ("p", "patch")):
        body = {"name": name, "kind": kind, "target_mhz": 433.0}
        assert client.post("/api/antennas", json=body).status_code == 200
    for antenna_id, sample, note in ((1, "good", "first"), (1, "narrow", "second"),
                                     (2, "patch_good", "patch")):  # fmt: skip
        body = {"antenna_id": antenna_id, "source": "synthetic", "sample": sample,
                "cal_mode": "vna", "change_note": note}  # fmt: skip
        response = client.post("/api/measurements", json=body)
        assert response.status_code == 200, response.text[:200]
    return path


def rows(db: Path, table: str) -> list[tuple]:
    with sqlite3.connect(db) as conn:
        return conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()


def test_copies_only_the_chosen_measurements_and_their_antennas(
    source: Path, tmp_path: Path
) -> None:
    out = tmp_path / "demo.db"

    count = export_measurements(source, out, [3, 1])

    assert count == 2
    assert [row[0] for row in rows(out, "measurements")] == [1, 3]
    assert rows(out, "measurements") == [r for r in rows(source, "measurements") if r[0] != 2]
    assert rows(out, "antennas") == rows(source, "antennas")


def test_antenna_without_a_chosen_measurement_is_left_out(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "demo.db"

    export_measurements(source, out, [2])

    assert [row[0] for row in rows(out, "antennas")] == [1]


def test_exported_database_shows_the_card_in_demo_mode(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "demo.db"
    export_measurements(source, out, [1])

    client = TestClient(create_app(out, mode="demo"))

    assert client.get("/api/measurements/1").json()["card"]["headline"]
    assert client.get("/api/measurements/1").json()["change_note"] == "first"


def test_replaces_an_older_demo_database(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "demo.db"
    export_measurements(source, out, [1, 2, 3])

    export_measurements(source, out, [3])

    assert [row[0] for row in rows(out, "measurements")] == [3]


@pytest.mark.parametrize(
    ("ids", "message"),
    [([1, 99], "99"), ([], "측정"), ([1, 1], "1")],
)
def test_bad_choice_writes_nothing(
    ids: list[int], message: str, source: Path, tmp_path: Path
) -> None:
    out = tmp_path / "demo.db"

    with pytest.raises(ExportError, match=message):
        export_measurements(source, out, ids)
    assert not out.exists()
    assert list(tmp_path.iterdir()) == [source]


def test_bad_choice_keeps_the_older_demo_database(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "demo.db"
    export_measurements(source, out, [1])

    with pytest.raises(ExportError):
        export_measurements(source, out, [99])

    assert [row[0] for row in rows(out, "measurements")] == [1]


def test_refuses_to_write_over_the_source(source: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The same file through another spelling: relative, and through `..`."""
    before = rows(source, "measurements")
    (source.parent / "sub").mkdir()
    monkeypatch.chdir(source.parent / "sub")

    for out in (Path("..") / source.name, source.parent / "sub" / ".." / source.name):
        with pytest.raises(ExportError, match="원본"):
            export_measurements(source, out, [1])
    with pytest.raises(ExportError, match="원본"):
        export_measurements(Path("..") / source.name, source, [1])
    assert rows(source, "measurements") == before


def test_refuses_another_name_of_the_same_file(source: Path) -> None:
    """A hard link (or another letter case on macOS) names the source without resolving to it."""
    other_name = source.parent / "link.db"
    other_name.hardlink_to(source)
    before = rows(source, "measurements")

    with pytest.raises(ExportError, match="원본"):
        export_measurements(source, other_name, [1])
    assert rows(source, "measurements") == before


def test_refuses_the_source_in_other_letter_case(source: Path) -> None:
    upper = source.with_name(source.name.upper())
    if not upper.exists():
        pytest.skip("this disk tells letter cases apart")
    before = rows(source, "measurements")

    with pytest.raises(ExportError, match="원본"):
        export_measurements(source, upper, [1])
    assert rows(source, "measurements") == before


def test_leaves_an_unrelated_part_file_alone(source: Path) -> None:
    out = source.parent / "demo.db"
    unrelated = source.parent / "demo.db.part"
    unrelated.write_text("not ours", encoding="utf-8")

    export_measurements(source, out, [1])

    assert unrelated.read_text(encoding="utf-8") == "not ours"
    assert sorted(p.name for p in source.parent.iterdir()) == [
        "antenna.db",
        "demo.db",
        "demo.db.part",
    ]


def test_id_too_large_for_sqlite_is_a_choice_error(source: Path, tmp_path: Path) -> None:
    out = tmp_path / "demo.db"

    with pytest.raises(ExportError, match=str(2**70)):
        export_measurements(source, out, [1, 2**70])
    assert not out.exists()


def test_missing_source_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ExportError, match="없습니다"):
        export_measurements(tmp_path / "nope.db", tmp_path / "demo.db", [1])
    assert list(tmp_path.iterdir()) == []


# scripts/export_demo.py


def test_script_without_ids_lists_the_choices_and_writes_nothing(
    source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = source.parent / "demo.db"

    code = export_demo.main(["--db", str(source), "--out", str(out)])

    lines = capsys.readouterr().out.splitlines()
    assert code == 0
    assert [line.split("\t")[:2] for line in lines[1:4]] == [["1", "m"], ["2", "m"], ["3", "p"]]
    assert not out.exists()


def test_script_writes_demo_db_next_to_antenna_db_by_default(
    source: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(export_demo, "ROOT", source.parent)  # source is <tmp>/antenna.db

    code = export_demo.main(["3"])

    assert code == 0
    assert [row[0] for row in rows(source.parent / "demo.db", "measurements")] == [3]
    assert "1개" in capsys.readouterr().out


@pytest.mark.parametrize("args", [["99"], ["1", "1"]])
def test_script_reports_a_bad_choice_with_exit_code_1(
    args: list[str], source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = source.parent / "demo.db"

    code = export_demo.main([*args, "--db", str(source), "--out", str(out)])

    assert code == 1
    assert capsys.readouterr().err.strip()
    assert not out.exists()


def test_script_says_when_the_list_is_cut(
    source: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(export_demo, "LIST_LIMIT", 2)

    export_demo.main(["--db", str(source)])

    out = capsys.readouterr().out
    assert "최근 2개만" in out
    assert [line.split("\t")[0] for line in out.splitlines()[1:3]] == ["2", "3"]


def test_script_does_not_warn_when_the_list_is_whole(
    source: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    export_demo.main(["--db", str(source)])

    assert "만 표시" not in capsys.readouterr().out


def test_script_listing_a_missing_db_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = export_demo.main(["--db", str(tmp_path / "nope.db")])

    assert code == 1
    assert "없습니다" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []
