"""Assembly only: build the FastAPI app and wire routes. No business logic here."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

WEB_DIST = Path(__file__).resolve().parent / "web" / "dist"

app = FastAPI(title="Antenna S11 Helper")


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"mode": "local", "ollama": False, "ports": []}


# Mounted last so /api routes win over the static catch-all.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
