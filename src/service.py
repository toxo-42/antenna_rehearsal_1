"""Measurement workflow: check input, judge a sweep with the core, store it, shape responses.

Errors carry a Korean message for the student: InputError (422), NotFoundError (404),
TooLargeError (413), BusyError (409), DeviceError (503).
"""

import json
import math
import threading
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from src import saa2, saa2_screen, store
from src.classify import classify
from src.models import Antenna, AntennaKind, CalMode, CardStage, Sweep
from src.sources import SOURCE_VALUES, SweepSource, SyntheticSource
from src.sweep_parser import HZ_PER_MHZ, check_sweep, parse_sweep_csv
from src.synthetic import SAMPLE_NAMES, make_sample
from src.verdict import build_card

MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_LIMIT = 200
UNCALIBRATED_SOURCES = ("usb",)  # SAA-2 USB values do not include the device calibration
Row = dict[str, Any]


class InputError(ValueError):
    """Invalid input (HTTP 422)."""


class NotFoundError(LookupError):
    """An id that does not exist (HTTP 404)."""


class TooLargeError(ValueError):
    """An upload over MAX_UPLOAD_BYTES (HTTP 413)."""


class BusyError(RuntimeError):
    """A USB measurement is already running (HTTP 409)."""


class DeviceError(RuntimeError):
    """The measuring device failed; nothing was saved (HTTP 503)."""


@dataclass(frozen=True)
class AntennaInput:
    name: str
    kind: str
    target_mhz: float


@dataclass(frozen=True)
class MeasureInput:
    antenna_id: int
    cal_mode: str
    change_note: str
    length_cm: float | None = None  # conductor length now, already checked (`checked_length`)


@dataclass(frozen=True)
class UsbInput:
    port: str | None
    start_mhz: float | None
    stop_mhz: float | None
    points: int | None


@dataclass(frozen=True)
class ListInput:
    antenna_id: int | None = None
    stage: str | None = None
    limit: int = 50
    offset: int = 0


def create_antenna(db_path: Path, data: AntennaInput) -> Row:
    _check_choice("kind", data.kind, [kind.value for kind in AntennaKind])
    if not data.name.strip():
        raise InputError("안테나 이름(name)을 입력해 주세요.")
    if not (math.isfinite(data.target_mhz) and data.target_mhz > 0):
        raise InputError("목표 주파수(target_mhz)는 0보다 큰 유한한 수여야 합니다.")
    with store.connect(db_path) as conn:
        antenna_id = store.insert_antenna(conn, data.name, data.kind, data.target_mhz)
    return {"id": antenna_id, "name": data.name, "kind": data.kind, "target_mhz": data.target_mhz}


def list_antennas(db_path: Path) -> list[Row]:
    with store.connect(db_path) as conn:
        return json_safe(store.list_antennas(conn))


def list_samples() -> list[Row]:
    """Synthetic samples for the picker. Their antenna is a hint only; the verdict uses the DB's."""
    antennas = [make_sample(name).antenna for name in SAMPLE_NAMES]
    return [{"name": a.name, "kind": a.kind.value, "target_mhz": a.target_mhz} for a in antennas]


def synthetic_source(source: str, sample: str | None) -> SweepSource:
    """The synthetic source for `POST /api/measurements` (`usb` goes through `usb_source`)."""
    _check_choice("source", source, list(SOURCE_VALUES))
    if source != "synthetic":
        raise InputError(
            f"source '{source}'는 여기서 받지 않습니다. synthetic과 usb만 됩니다 "
            "(CSV는 /api/measurements/upload로 올려 주세요)."
        )
    if sample is None:
        raise InputError("합성 샘플 이름(sample)이 필요합니다.")
    try:
        return SyntheticSource(sample)
    except KeyError:
        raise InputError(f"'{sample}'은(는) 없는 합성 샘플입니다.") from None


def usb_source(data: UsbInput, opener: saa2.Opener) -> saa2.Saa2Source:
    """Check a USB request before the device is touched."""
    if data.port is None or not data.port.strip():
        raise InputError("USB 포트(port)를 골라 주세요.")
    if data.start_mhz is None or data.stop_mhz is None or data.points is None:
        raise InputError("시작 MHz(start_mhz), 종료 MHz(stop_mhz), 점 개수(points)가 필요합니다.")
    try:
        sweep_range = saa2.make_range(data.start_mhz, data.stop_mhz, data.points)
    except ValueError as error:
        raise InputError(str(error)) from None
    return saa2.Saa2Source(data.port, sweep_range, opener)


def measure_usb(
    db_path: Path, source: saa2.Saa2Source, request: MeasureInput, lock: threading.Lock
) -> Row:
    """Measure on the SAA-2 and save (as `cal_mode = unknown`, see `stored_cal_mode`). One
    measurement at a time; a second one meanwhile is BusyError."""
    antenna = _antenna_for(db_path, request)
    axis = saa2.axis_hz(source.sweep_range)  # the points the device will measure, not the request
    _check_target_in(axis[0] / HZ_PER_MHZ, axis[-1] / HZ_PER_MHZ, antenna)
    if not lock.acquire(blocking=False):
        raise BusyError("다른 USB 측정이 진행 중입니다. 끝난 뒤 다시 눌러 주세요.")
    try:
        sweep = source.read()
    except saa2.DeviceError as error:
        raise DeviceError(str(error)) from None
    finally:
        lock.release()
    return _save(db_path, sweep, source.source, antenna, request)


def device_screen(port: str | None, opener: saa2.Opener, lock: threading.Lock) -> bytes:
    """The SAA-2 screen as PNG. Not while a USB measurement holds the port (BusyError)."""
    if port is None or not port.strip():
        raise InputError("USB 포트(port)를 골라 주세요.")
    if not lock.acquire(blocking=False):
        raise BusyError("USB 측정이 진행 중입니다. 끝난 뒤 다시 시도해 주세요.")
    try:
        return saa2_screen.capture_png(port, opener)
    except saa2.DeviceError as error:
        raise DeviceError(str(error)) from None
    finally:
        lock.release()


def measure(db_path: Path, source: SweepSource, request: MeasureInput) -> Row:
    """Read a sweep from any source, judge it against the stored antenna, and save it."""
    _check_choice("source", source.source, list(SOURCE_VALUES))
    antenna = _antenna_for(db_path, request)
    try:
        sweep = source.read()
    except LookupError as error:
        raise NotFoundError(str(error)) from None
    return _save(db_path, sweep, source.source, antenna, request)


def measure_csv(db_path: Path, data: bytes, request: MeasureInput) -> Row:
    """Judge and save an uploaded CSV file (UTF-8, BOM allowed)."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise TooLargeError("파일이 2 MB를 넘습니다. 측정점 수를 줄여 다시 올려 주세요.")
    antenna = _antenna_for(db_path, request)
    try:
        sweep = parse_sweep_csv(data.decode("utf-8-sig"))
    except UnicodeDecodeError:
        raise InputError("파일을 UTF-8 텍스트로 읽을 수 없습니다. CSV를 UTF-8로 저장해 주세요.")
    except ValueError as error:
        raise InputError(str(error)) from None
    return _save(db_path, sweep, "csv", antenna, request)


COPIED_COLUMNS = ("source", "cal_mode", "measured_at", "change_note", "length_cm",
                  "resonance_mhz", "s11_db", "bandwidth_pct")  # fmt: skip


def get_measurement(db_path: Path, measurement_id: int) -> Row:
    """One measurement in the shape of contract/measurement.json."""
    with store.connect(db_path) as conn:
        row = store.get_measurement(conn, measurement_id)
        if row is None:
            raise NotFoundError(f"측정 {measurement_id}번이 없습니다.")
        antenna = store.get_antenna(conn, row["antenna_id"])
    sweep = store.sweep_from_json(row["sweep_json"])
    return json_safe(
        {
            "id": row["id"],
            "antenna": antenna,
            **{key: row[key] for key in COPIED_COLUMNS},
            "sweep": [
                {"f_mhz": f_mhz, "s11_db": s11_db}
                for f_mhz, s11_db in zip(sweep.f_mhz, sweep.s11_db, strict=True)
            ],
            "card": json.loads(row["card_json"]),
        }
    )


def list_measurements(db_path: Path, query: ListInput) -> list[Row]:
    if query.stage is not None:
        _check_choice("stage", query.stage, [stage.value for stage in CardStage])
    if not 1 <= query.limit <= MAX_LIMIT:
        raise InputError(f"limit은 1 이상 {MAX_LIMIT} 이하여야 합니다.")
    if not 0 <= query.offset <= store.SQLITE_MAX_INT:
        raise InputError(f"offset은 0 이상 {store.SQLITE_MAX_INT} 이하여야 합니다.")
    store_query = store.MeasurementQuery(query.antenna_id, query.stage, query.limit, query.offset)
    with store.connect(db_path) as conn:
        return json_safe(store.list_measurements(conn, store_query))


def stored_cal_mode(source: str, cal_mode: str) -> str:
    """The calibration saved with a measurement. Sources in UNCALIBRATED_SOURCES never carry the
    device calibration, so they are `unknown` whatever was asked."""
    return CalMode.UNKNOWN.value if source in UNCALIBRATED_SOURCES else cal_mode


def json_safe(value: Any) -> Any:
    """Replace NaN and infinities with None at any depth, so responses never carry them."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [json_safe(item) for item in value]
    return value


def _check_choice(name: str, value: str, allowed: list[str]) -> None:
    if value not in allowed:
        raise InputError(f"{name}는 {', '.join(allowed)} 중 하나여야 합니다 (받은 값: '{value}').")


def _antenna_for(db_path: Path, request: MeasureInput) -> Antenna:
    _check_choice("cal_mode", request.cal_mode, [mode.value for mode in CalMode])
    with store.connect(db_path) as conn:
        row = store.get_antenna(conn, request.antenna_id)
    if row is None:
        raise NotFoundError(f"안테나 {request.antenna_id}번이 없습니다.")
    kind = AntennaKind(row["kind"])  # the length is the monopole's conductor; a patch has none
    length_cm = request.length_cm if kind is AntennaKind.MONOPOLE else None
    return Antenna(row["name"], kind, row["target_mhz"], length_cm)


def _check_target_in(low: float, high: float, antenna: Antenna) -> None:
    target_mhz = antenna.target_mhz
    if target_mhz < low or target_mhz > high:
        raise InputError(
            f"목표 {target_mhz:g} MHz가 측정 범위 {low:.2f}~{high:.2f} MHz 밖입니다. "
            "목표가 들어가도록 범위를 정해 다시 측정해 주세요."
        )


def _save(db_path: Path, sweep: Sweep, source: str, antenna: Antenna, request: MeasureInput) -> Row:
    try:
        check_sweep(sweep)
    except ValueError as error:
        raise InputError(str(error)) from None
    _check_target_in(sweep.f_mhz[0], sweep.f_mhz[-1], antenna)
    new = _new_measurement(sweep, source, antenna, request)
    with store.connect(db_path) as conn:
        measurement_id = store.insert_measurement(conn, new)
    return get_measurement(db_path, measurement_id)


def _new_measurement(
    sweep: Sweep, source: str, antenna: Antenna, request: MeasureInput
) -> store.NewMeasurement:
    request = replace(request, cal_mode=stored_cal_mode(source, request.cal_mode))
    card = build_card(sweep, antenna, CalMode(request.cal_mode))
    selected = classify(sweep, antenna).selected
    return store.NewMeasurement(
        antenna_id=request.antenna_id,
        measured_at=datetime.now().isoformat(timespec="seconds"),
        source=source,
        cal_mode=request.cal_mode,
        stage=card.stage.value,
        resonance_mhz=selected.f_mhz if selected else None,
        s11_db=selected.s11_db if selected else None,
        bandwidth_pct=selected.bandwidth_pct if selected else None,
        sweep_json=store.sweep_to_json(sweep),
        card_json=json.dumps(asdict(card), ensure_ascii=False),
        change_note=request.change_note,
        length_cm=antenna.length_cm,
    )
