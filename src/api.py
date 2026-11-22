"""HTTP routes. They only translate between HTTP and `service`; all rules live in `service`."""

import threading
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, StrictFloat, StrictInt
from starlette.exceptions import HTTPException

from src import assist, compare, saa2, service

router = APIRouter(prefix="/api")

ERROR_STATUS: dict[type[Exception], int] = {
    service.InputError: 422,
    service.NotFoundError: 404,
    service.TooLargeError: 413,
    service.BusyError: 409,
    service.DeviceError: 503,
}
DEMO_REFUSAL = (
    "시연 모드에서는 저장된 측정만 볼 수 있습니다. "
    "안테나 추가, 측정 저장, 파일 업로드, USB 장비는 쓸 수 없습니다."
)


class AntennaBody(BaseModel):
    name: str
    kind: str
    target_mhz: StrictFloat  # takes 433 and 433.0, refuses true and "433"


class MeasurementBody(BaseModel):
    antenna_id: StrictInt
    source: str
    sample: str | None = None
    cal_mode: str
    change_note: str = ""
    port: str | None = None  # source = usb only, with the three below
    start_mhz: StrictFloat | None = None
    stop_mhz: StrictFloat | None = None
    points: StrictInt | None = None


class QuestionBody(BaseModel):
    question: str


def install(app: FastAPI, db_path: Path, parts: assist.LlmParts, read_only: bool = False) -> None:
    """Attach the routes and the Korean error responses to an app that uses `db_path`.

    `read_only` (demo mode) answers every write and every USB route with 403.
    """
    app.state.db_path = db_path
    app.state.read_only = read_only
    app.state.llm = parts
    app.state.serial_opener = saa2.open_serial
    app.state.usb_lock = threading.Lock()
    app.include_router(router)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _body_error)
    for error_type in ERROR_STATUS:
        app.add_exception_handler(error_type, _service_error)


def _db(request: Request) -> Path:
    return request.app.state.db_path


def _llm(request: Request) -> assist.LlmParts:
    return request.app.state.llm


def _writable(request: Request) -> None:
    """Runs before the route, so a refused request never reaches the database or a port."""
    if request.app.state.read_only:
        raise HTTPException(status_code=403, detail=DEMO_REFUSAL)


WRITABLE = [Depends(_writable)]


def status_for(exc: Exception) -> int:
    """HTTP status for a service error, subclasses included."""
    return next(status for kind, status in ERROR_STATUS.items() if isinstance(exc, kind))


async def _service_error(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status_for(exc), content={"detail": str(exc)})


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    fields = [".".join(str(part) for part in e["loc"] if part != "body") for e in errors]
    detail = f"입력값이 없거나 형식이 올바르지 않습니다: {', '.join(fields) or '요청'}"
    return JSONResponse(status_code=422, content={"detail": detail})


async def _body_error(request: Request, exc: Exception) -> Any:
    """The framework answers an unreadable body (e.g. broken multipart) with an English 400."""
    if isinstance(exc, HTTPException) and exc.status_code == 400:
        detail = "요청 본문을 읽을 수 없습니다. CSV 파일과 입력값을 multipart 형식으로 보내 주세요."
        return JSONResponse(status_code=422, content={"detail": detail})
    return await http_exception_handler(request, exc)  # type: ignore[arg-type]


@router.get("/antennas")
def list_antennas(request: Request) -> list[dict[str, Any]]:
    return service.list_antennas(_db(request))


@router.post("/antennas", dependencies=WRITABLE)
def create_antenna(request: Request, body: AntennaBody) -> dict[str, Any]:
    data = service.AntennaInput(name=body.name, kind=body.kind, target_mhz=body.target_mhz)
    return service.create_antenna(_db(request), data)


@router.get("/samples")
def list_samples() -> list[dict[str, Any]]:
    return service.list_samples()


@router.get("/ports", dependencies=WRITABLE)
def list_ports() -> list[str]:
    return saa2.list_ports()


@router.get("/device/screen", dependencies=WRITABLE)
def device_screen(request: Request, port: str | None = None) -> Response:
    state = request.app.state
    png = service.device_screen(port, state.serial_opener, state.usb_lock)
    return Response(content=png, media_type="image/png")


@router.post("/measurements", dependencies=WRITABLE)
def create_measurement(request: Request, body: MeasurementBody) -> dict[str, Any]:
    measure = service.MeasureInput(body.antenna_id, body.cal_mode, body.change_note)
    if body.source == "usb":
        usb = service.UsbInput(body.port, body.start_mhz, body.stop_mhz, body.points)
        source = service.usb_source(usb, request.app.state.serial_opener)
        return service.measure_usb(_db(request), source, measure, request.app.state.usb_lock)
    synthetic = service.synthetic_source(body.source, body.sample)
    return service.measure(_db(request), synthetic, measure)


@router.post("/measurements/upload", dependencies=WRITABLE)
def upload_measurement(
    request: Request,
    file: Annotated[UploadFile, File()],
    antenna_id: Annotated[int, Form()],
    cal_mode: Annotated[str, Form()],
    change_note: Annotated[str, Form()] = "",
) -> dict[str, Any]:
    data = file.file.read(service.MAX_UPLOAD_BYTES + 1)
    measure = service.MeasureInput(antenna_id, cal_mode, change_note)
    return service.measure_csv(_db(request), data, measure)


@router.get("/measurements")
def list_measurements(
    request: Request,
    antenna_id: int | None = None,
    stage: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    query = service.ListInput(antenna_id, stage, limit, offset)
    return service.list_measurements(_db(request), query)


@router.get("/compare")
def compare_measurements(request: Request, before: int, after: int) -> dict[str, Any]:
    return compare.compare_measurements(_db(request), before, after)


@router.get("/measurements/{measurement_id}")
def get_measurement(request: Request, measurement_id: int) -> dict[str, Any]:
    return service.get_measurement(_db(request), measurement_id)


@router.post("/measurements/{measurement_id}/explain")
def explain_measurement(request: Request, measurement_id: int) -> dict[str, Any]:
    return assist.explain_measurement(_db(request), measurement_id, _llm(request).explainer)


@router.post("/measurements/{measurement_id}/ask")
def ask_measurement(request: Request, measurement_id: int, body: QuestionBody) -> dict[str, Any]:
    router_part = _llm(request).router
    return assist.ask_measurement(_db(request), measurement_id, body.question, router_part)


@router.get("/measurements/{measurement_id}/guides")
def guide_choices(request: Request, measurement_id: int) -> list[dict[str, Any]]:
    return assist.guide_choices(_db(request), measurement_id)
