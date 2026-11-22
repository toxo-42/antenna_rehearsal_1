"""Assembly only: build the FastAPI app and wire routes. No business logic here."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src import api, assist, store

ROOT = Path(__file__).resolve().parent
WEB_DIST = ROOT / "web" / "dist"
DEFAULT_DB = ROOT / "antenna.db"


def create_app(db_path: Path = DEFAULT_DB, parts: assist.LlmParts | None = None) -> FastAPI:
    """`parts` defaults to what OLLAMA_MODEL and OLLAMA_EXPLAIN select."""
    app = FastAPI(title="Antenna S11 Helper")
    llm = parts if parts is not None else assist.parts_from_env(os.environ)

    @app.get("/api/health")
    def health() -> dict[str, object]:
        return {"mode": "local", **assist.health_flags(llm), "ports": []}

    store.init_db(db_path)
    api.install(app, db_path, llm)

    # Mounted last so /api routes win over the static catch-all.
    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    return app


app = create_app()
