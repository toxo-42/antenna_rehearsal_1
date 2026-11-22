"""Parse an S11 sweep from CSV text. Errors are ValueError with a Korean message for the student."""

import csv
import io
import itertools
import math
from collections.abc import Iterator

from src.models import Sweep

REQUIRED_COLUMNS = ("Frequency_Hz", "S11_dB")
COMPLEX_COLUMNS = ("S11_real", "S11_imag")
KNOWN_COLUMNS = REQUIRED_COLUMNS + COMPLEX_COLUMNS
MIN_POINTS = 3
HZ_PER_MHZ = 1_000_000.0
# Allowed range per column. Far wider than any real VNA, and narrow enough that every value
# the verdict derives (depth, offset %, band %, mode ratio, impedance) stays finite.
LIMITS: dict[str, tuple[float, float]] = {
    "Frequency_Hz": (1.0, 1e12),
    "S11_dB": (-1000.0, 1000.0),
    "S11_real": (-1000.0, 1000.0),
    "S11_imag": (-1000.0, 1000.0),
}
RANGE_TEXT = "주파수 1 Hz~1 THz, S11 -1000~1000 dB, S11_real·S11_imag -1000~1000"


def parse_sweep_csv(text: str) -> Sweep:
    """Read `Frequency_Hz,S11_dB` (and optional `S11_real,S11_imag`); other columns are ignored."""
    reader = csv.reader(io.StringIO(text.lstrip("﻿"), newline=""), strict=True)
    try:
        return _read_sweep(reader)
    except csv.Error:
        raise ValueError(
            f"{reader.line_num}행: CSV 형식이 올바르지 않습니다. 따옴표가 닫혔는지 확인해 주세요."
        ) from None


def _read_sweep(reader: Iterator[list[str]]) -> Sweep:
    header = next(reader, None)
    if header is None or _is_blank(header):
        raise ValueError("CSV가 비어 있습니다. 첫 줄에 Frequency_Hz,S11_dB 헤더가 필요합니다.")
    columns = _column_indexes(header)
    has_complex = all(name in columns for name in COMPLEX_COLUMNS)
    names = REQUIRED_COLUMNS + (COMPLEX_COLUMNS if has_complex else ())
    rows = [
        (reader.line_num, _read_row(row, reader.line_num, [(n, columns[n]) for n in names]))
        for row in reader
        if not _is_blank(row)
    ]
    _check_points(rows)
    values = [row for _, row in rows]
    return Sweep(
        f_mhz=tuple(row[0] / HZ_PER_MHZ for row in values),
        s11_db=tuple(row[1] for row in values),
        gamma=tuple(complex(row[2], row[3]) for row in values) if has_complex else None,
    )


def _is_blank(row: list[str]) -> bool:
    return not any(cell.strip() for cell in row)


def _column_indexes(header: list[str]) -> dict[str, int]:
    names = [name.strip() for name in header]
    repeated = [name for name in KNOWN_COLUMNS if names.count(name) > 1]
    if repeated:
        raise ValueError(f"CSV 헤더에 {repeated[0]} 열이 두 번 있습니다. 하나만 남겨 주세요.")
    columns = {name: index for index, name in enumerate(names)}
    missing = [name for name in REQUIRED_COLUMNS if name not in columns]
    if missing:
        raise ValueError(
            f"CSV 헤더에 {', '.join(missing)} 열이 없습니다. "
            "첫 줄에 Frequency_Hz,S11_dB가 있어야 합니다."
        )
    return columns


def _read_row(row: list[str], line: int, columns: list[tuple[str, int]]) -> list[float]:
    return [_number(row, line, name, index) for name, index in columns]


def _number(row: list[str], line: int, name: str, index: int) -> float:
    cell = row[index].strip() if index < len(row) else ""
    try:
        value = float(cell)
    except ValueError:
        raise ValueError(f"{line}행: {name} 값 '{cell}'은(는) 숫자가 아닙니다.") from None
    if not math.isfinite(value):
        raise ValueError(f"{line}행: {name} 값 '{cell}'은(는) 유한한 수가 아닙니다.")
    low, high = LIMITS[name]
    if not low <= value <= high:
        raise ValueError(
            f"{line}행: {name} 값 '{cell}'이(가) 허용 범위({low:g}~{high:g})를 벗어났습니다."
        )
    return value


def check_sweep(sweep: Sweep) -> None:
    """The CSV checks for a sweep from any source: 3+ points, finite numbers in LIMITS, rising
    frequency."""
    count = len(sweep.f_mhz)
    gamma = sweep.gamma if sweep.gamma is not None else ()
    if len(sweep.s11_db) != count or (sweep.gamma is not None and len(gamma) != count):
        raise ValueError("측정값의 주파수, S11, 반사계수 점 수가 서로 맞지 않습니다.")
    if count < MIN_POINTS:
        raise ValueError(f"측정점이 {MIN_POINTS}점 이상 필요합니다 (현재 {count}점).")
    low_hz, high_hz = LIMITS["Frequency_Hz"]
    # Compared in MHz: dividing is monotonic, so this agrees with the parser's check in Hz.
    columns = [
        (sweep.f_mhz, (low_hz / HZ_PER_MHZ, high_hz / HZ_PER_MHZ)),
        (sweep.s11_db, LIMITS["S11_dB"]),
        ([g.real for g in gamma], LIMITS["S11_real"]),
        ([g.imag for g in gamma], LIMITS["S11_imag"]),
    ]
    if not all(math.isfinite(v) for values, _ in columns for v in values):
        raise ValueError("측정값에 유한한 수가 아닌 값(NaN, 무한대)이 있습니다.")
    if not all(low <= v <= high for values, (low, high) in columns for v in values):
        raise ValueError(f"측정값이 허용 범위를 벗어났습니다 ({RANGE_TEXT}).")
    if any(upper <= lower for lower, upper in itertools.pairwise(sweep.f_mhz)):
        raise ValueError("주파수가 오름차순이 아닙니다. 낮은 주파수부터 있어야 합니다.")


def _check_points(rows: list[tuple[int, list[float]]]) -> None:
    if len(rows) < MIN_POINTS:
        raise ValueError(f"측정점이 {MIN_POINTS}점 이상 필요합니다 (현재 {len(rows)}점).")
    for (_, previous), (line, current) in itertools.pairwise(rows):
        if current[0] <= previous[0]:
            raise ValueError(
                f"{line}행: 주파수가 오름차순이 아닙니다. 낮은 주파수부터 적어 주세요."
            )
