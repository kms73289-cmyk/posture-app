"""FastAPI 앱: CORS, API, frontend/dist 정적 서빙, 분석기 프리로드."""
from __future__ import annotations

import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config import DATA_FILE
from data_manager import DataManager
from settings_manager import AppSettings
from backend.monitor_service import MonitorService
from backend.routes import build_router

DIST = ROOT / "frontend" / "dist"

data_manager = DataManager(DATA_FILE)
app_settings = AppSettings()
monitor = MonitorService(data_manager, app_settings)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    threading.Thread(target=monitor.preload_analyzer, daemon=True).start()
    yield
    monitor.shutdown()


app = FastAPI(title="바른자세", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(build_router(monitor, data_manager, app_settings))


@app.get("/api/health")
def health():
    return {"ok": True}


if DIST.is_dir():
    assets = DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws"):
            return FileResponse(DIST / "index.html", status_code=404)
        candidate = DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST / "index.html")
