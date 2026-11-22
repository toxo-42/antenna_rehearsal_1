"""Copy chosen measurements from the current database into `demo.db` for APP_MODE=demo.

Usage:
  uv run python scripts/export_demo.py              list the measurements to choose from
  uv run python scripts/export_demo.py 3 5 7        write demo.db with measurements 3, 5, 7
Options: --db PATH (default: antenna.db), --out PATH (default: demo.db). Exit code 1 on error.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import store
from src.demo_export import ExportError, export_measurements

LIST_LIMIT = 1000


def print_choices(db_path: Path) -> int:
    if not db_path.is_file():
        print(f"원본 DB가 없습니다: {db_path}", file=sys.stderr)
        return 1
    with store.connect(db_path) as conn:
        names = {row["id"]: row["name"] for row in store.list_antennas(conn)}
        # One extra row tells whether the list was cut; newest rows come first.
        rows = store.list_measurements(conn, store.MeasurementQuery(limit=LIST_LIMIT + 1))
    print("id\t안테나\t측정 시각\t출처\t단계\t메모")
    for row in sorted(rows[:LIST_LIMIT], key=lambda r: r["id"]):
        antenna = names.get(row["antenna_id"], "?")
        print(f"{row['id']}\t{antenna}\t{row['measured_at']}\t{row['source']}\t"
              f"{row['stage']}\t{row['change_note']}")  # fmt: skip
    if len(rows) > LIST_LIMIT:
        print(
            f"\n(측정이 더 있습니다. 최근 {LIST_LIMIT}개만 표시했습니다. 더 오래된 id도 고를 수 있습니다.)"
        )
    print("\n고를 측정 id를 인자로 주세요. 예: uv run python scripts/export_demo.py 3 5 7")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="고른 측정만 demo.db로 복사")
    parser.add_argument("ids", nargs="*", type=int, help="내보낼 측정 id")
    parser.add_argument("--db", type=Path, default=ROOT / "antenna.db")
    parser.add_argument("--out", type=Path, default=ROOT / "demo.db")
    args = parser.parse_args(argv)
    if not args.ids:
        return print_choices(args.db)
    try:
        count = export_measurements(args.db, args.out, args.ids)
    except ExportError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"측정 {count}개를 {args.out}에 저장했습니다. 실행: APP_MODE=demo uv run uvicorn app:app")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
