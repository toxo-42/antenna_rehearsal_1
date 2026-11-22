"""HTTP routes. They only translate between HTTP and `service`; all rules live in `service`."""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, FastAPI, File, Form, Request, UploadFile
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictFloat, StrictInt
from starlette.exceptions import HTTPException

from src import service

router = APIRouter(prefix="/api")

ERROR_STATUS: dict[type[Exception], int] = {
    service.InputError: 422,
    service.NotFoundError: 404,
    service.TooLargeError: 413,
}


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


def install(app: FastAPI, db_path: Path) -> None:
    """Attach the routes and the Korean error responses to an app that uses `db_path`."""
    app.state.db_path = db_path
    app.include_router(router)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _body_error)
    for error_type in ERROR_STATUS:
        app.add_exception_handler(error_type, _service_error)


def _db(request: Request) -> Path:
    return request.app.state.db_path


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


@router.post("/antennas")
def create_antenna(request: Request, body: AntennaBody) -> dict[str, Any]:
    data = service.AntennaInput(name=body.name, kind=body.kind, target_mhz=body.target_mhz)
    return service.create_antenna(_db(request), data)


@router.get("/samples")
def list_samples() -> list[dict[str, Any]]:
    return service.list_samples()


@router.post("/measurements")
def create_measurement(request: Request, body: MeasurementBody) -> dict[str, Any]:
    source = service.synthetic_source(body.source, body.sample)
    measure = service.MeasureInput(body.antenna_id, body.cal_mode, body.change_note)
    return service.measure(_db(request), source, measure)


@router.post("/measurements/upload")
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


@router.get("/measurements/{measurement_id}")
def get_measurement(request: Request, measurement_id: int) -> dict[str, Any]:
    return service.get_measurement(_db(request), measurement_id)
