"""Assembly only: build the FastAPI app and wire routes. No business logic here."""

import os
from collections.abc import Mapping
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src import api, assist, store
from src.explain import NoExplainer
from src.router import NoRouter

ROOT = Path(__file__).resolve().parent
WEB_DIST = ROOT / "web" / "dist"
DEFAULT_DB = ROOT / "antenna.db"
DEMO_DB = ROOT / "demo.db"
MODES = ("local", "demo")


def create_app_from_env(env: Mapping[str, str]) -> FastAPI:
    """APP_MODE=demo serves `demo.db` read-only; unset or "local" serves `antenna.db`."""
    mode = env.get("APP_MODE", "").strip().lower() or "local"
    return create_app(None, assist.parts_from_env(env), mode)


def create_app(
    db_path: Path | None = None, parts: assist.LlmParts | None = None, mode: str = "local"
) -> FastAPI:
    """`db_path` defaults to `demo.db` in demo mode and `antenna.db` otherwise.

    `parts` defaults to what OLLAMA_MODEL and OLLAMA_EXPLAIN select; demo mode turns both off.
    """
    if mode not in MODES:
        raise ValueError(f"APP_MODE는 {' 또는 '.join(MODES)}여야 합니다: {mode!r}")
    demo = mode == "demo"
    db_path = db_path or (DEMO_DB if demo else DEFAULT_DB)
    if demo:
        _check_demo_db(db_path)
    # The built-in /docs and /redoc pages load their scripts from the internet: off.
    app = FastAPI(title="Antenna S11 Helper", docs_url=None, redoc_url=None)
    llm = parts if parts is not None else assist.parts_from_env(os.environ)
    if demo:
        llm = assist.LlmParts(NoExplainer(), NoRouter())

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"mode": mode, **assist.health_flags(llm), "ports": []}

    store.init_db(db_path)
    api.install(app, db_path, llm, read_only=demo)

    # Mounted last so /api routes win over the static catch-all.
    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    return app


def _check_demo_db(db_path: Path) -> None:
    """Demo mode never creates or fills its database: a missing or empty one stops the start."""
    hint = "먼저 `uv run python scripts/export_demo.py <측정 id...>`로 만드세요."
    if not db_path.is_file():
        raise FileNotFoundError(f"시연용 DB가 없습니다: {db_path}. {hint}")
    if store.count_measurements(db_path) == 0:
        raise ValueError(f"시연용 DB에 측정이 없습니다: {db_path}. {hint}")


def __getattr__(name: str) -> FastAPI:
    """`uvicorn app:app` asks for `app` here. Building it on request, not at import, keeps
    `from app import create_app` (tests, scripts) away from the real database."""
    if name == "app":
        return create_app_from_env(os.environ)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
