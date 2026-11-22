"""Before/after comparison of two measurements of one antenna.

The code decides the verdict. The summary only says what was changed and what happened after it;
it never names a cause.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src import change_note, store
from src.models import CardStage
from src.service import InputError, NotFoundError, json_safe
from src.store import HZ_PER_MHZ
from src.tolerance import at_least

CLOSER = "가까워짐"
FARTHER = "멀어짐"
SAME = "차이 없음(측정 간격 이내)"
NOT_COMPARABLE = "비교 불가"
NUMBER_KEYS = (
    "shift_mhz",
    "distance_before_mhz",
    "distance_after_mhz",
    "distance_change_mhz",
    "s11_change_db",
    "bandwidth_change_pct",
)
Row = dict[str, Any]
# A blocker looks at one side and returns why the pair cannot be compared, or None.
Blocker = Callable[[str, Row], str | None]


def _no_resonance(label: str, row: Row) -> str | None:
    if row["resonance_mhz"] is not None:
        return None
    return f"{label} 측정({row['id']}번)에 목표 근처의 공진이 없습니다."


def _invalid_stage(label: str, row: Row) -> str | None:
    if row["stage"] != CardStage.INVALID.value:
        return None
    return f"{label} 측정({row['id']}번)은 판정할 수 없는 측정(invalid)입니다."


BLOCKERS: tuple[Blocker, ...] = (_no_resonance, _invalid_stage)


def blocking_reasons(before: Row, after: Row) -> list[str]:
    """Every reason the pair cannot be compared, before's first."""
    sides = (("이전", before), ("이후", after))
    found = (blocker(label, row) for label, row in sides for blocker in BLOCKERS)
    return [reason for reason in found if reason is not None]


def distance_verdict(change_mhz: float, step: float) -> str:
    """A change in distance to the target below one measurement step is no difference."""
    if not at_least(abs(change_mhz), step):
        return SAME
    return CLOSER if change_mhz < 0 else FARTHER


def local_step_mhz(sweep_json: str, f_mhz: float) -> float:
    """The coarser gap on either side of the sweep point nearest `f_mhz`. A sweep may be dense
    only around the resonance, so the spacing there is what limits the reading."""
    freqs = [point[0] / HZ_PER_MHZ for point in json.loads(sweep_json)]
    i = min(range(len(freqs)), key=lambda k: abs(freqs[k] - f_mhz))
    gaps = [freqs[k + 1] - freqs[k] for k in (i - 1, i) if 0 <= k < len(freqs) - 1]
    return max(gaps)


def pair_step_mhz(before: Row, after: Row) -> float:
    """The coarser of the two local spacings: neither measurement resolves less than that."""
    rows = (before, after)
    return max(local_step_mhz(row["sweep_json"], row["resonance_mhz"]) for row in rows)


def _difference(after: float | None, before: float | None) -> float | None:
    return None if after is None or before is None else after - before


def _numbers(before: Row, after: Row, target_mhz: float) -> Row:
    distance_before = abs(before["resonance_mhz"] - target_mhz)
    distance_after = abs(after["resonance_mhz"] - target_mhz)
    return {
        "shift_mhz": after["resonance_mhz"] - before["resonance_mhz"],
        "distance_before_mhz": distance_before,
        "distance_after_mhz": distance_after,
        "distance_change_mhz": distance_after - distance_before,
        "s11_change_db": _difference(after["s11_db"], before["s11_db"]),
        "bandwidth_change_pct": _difference(after["bandwidth_pct"], before["bandwidth_pct"]),
    }


def _note_lead(after: Row) -> str:
    """What was changed, in the select boxes' words only. Free text is never repeated."""
    note = after["change_note"]
    if change_note.is_structured(note):
        return f"'{note}' 변경 뒤"
    if not note.strip():
        return f"이후 측정({after['id']}번)에 기록된 변경이 없습니다."
    return f"이후 측정({after['id']}번)의 메모는 선택 상자 형식이 아니라 요약에 넣지 않았습니다."


def _summary(result: Row, before: Row, after: Row) -> str:
    if not result["comparable"]:
        return f"{NOT_COMPARABLE}: {' '.join(result['reasons'])}"
    if before["id"] == after["id"]:
        return f"같은 측정({after['id']}번)끼리 비교했습니다: {result['verdict']}."
    return (
        f"{_note_lead(after)} 공진이 {before['resonance_mhz']:.2f} → "
        f"{after['resonance_mhz']:.2f} MHz ({result['shift_mhz']:+.2f} MHz)로 바뀌었고, "
        f"목표 {result['target_mhz']:g} MHz까지 거리는 {result['distance_before_mhz']:.2f} → "
        f"{result['distance_after_mhz']:.2f} MHz입니다: {result['verdict']}."
    )


def compare_rows(before: Row, after: Row, target_mhz: float, step: float | None) -> Row:
    """Compare two stored rows. `step` is the measurement spacing the verdict allows for; it is
    None only when a resonance is missing, and then the pair is not comparable anyway."""
    reasons = blocking_reasons(before, after)
    numbers = dict.fromkeys(NUMBER_KEYS) if reasons else _numbers(before, after, target_mhz)
    if reasons or step is None:
        verdict = NOT_COMPARABLE
    else:
        verdict = distance_verdict(numbers["distance_change_mhz"], step)
    result = {
        "before_id": before["id"],
        "after_id": after["id"],
        "target_mhz": target_mhz,
        "step_mhz": step,
        "comparable": not reasons,
        "verdict": verdict,
        "reasons": reasons,
        **numbers,
        "stage": {"before": before["stage"], "after": after["stage"]},
        "change_note": after["change_note"],
    }
    return {**result, "summary": _summary(result, before, after)}


def compare_measurements(db_path: Path, before_id: int, after_id: int) -> Row:
    """`GET /api/compare`. NotFoundError for a missing id, InputError for two antennas."""
    with store.connect(db_path) as conn:
        before, after = (_load(conn, measurement_id) for measurement_id in (before_id, after_id))
        if before["antenna_id"] != after["antenna_id"]:
            raise InputError(
                f"같은 안테나의 측정끼리만 비교할 수 있습니다 (측정 {before_id}번은 안테나 "
                f"{before['antenna_id']}번, 측정 {after_id}번은 안테나 {after['antenna_id']}번)."
            )
        antenna = store.get_antenna(conn, before["antenna_id"])
    if antenna is None:
        raise NotFoundError(f"안테나 {before['antenna_id']}번이 없습니다.")
    has_both = before["resonance_mhz"] is not None and after["resonance_mhz"] is not None
    step = pair_step_mhz(before, after) if has_both else None
    return json_safe(compare_rows(before, after, antenna["target_mhz"], step))


def _load(conn: Any, measurement_id: int) -> Row:
    row = store.get_measurement(conn, measurement_id)
    if row is None:
        raise NotFoundError(f"측정 {measurement_id}번이 없습니다.")
    return row
