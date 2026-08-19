from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .jobs import JobInfo, JobRequest, manager
from .runners import available_runners

app = FastAPI(title="OQP Studio backend", version=__version__)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/runners")
def runners() -> dict:
    return available_runners()


@app.post("/api/jobs")
def submit_job(req: JobRequest) -> JobInfo:
    return manager.submit(req)


@app.get("/api/jobs")
def list_jobs() -> list[JobInfo]:
    return manager.list()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> JobInfo:
    info = manager.get(job_id)
    if info is None:
        raise HTTPException(status_code=404, detail="job not found")
    return info


@app.get("/api/jobs/{job_id}/log")
def job_log(job_id: str) -> dict:
    if manager.get(job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"log": manager.log_tail(job_id)}


@app.get("/api/jobs/{job_id}/files")
def job_files(job_id: str) -> list[dict]:
    if manager.get(job_id) is None:
        raise HTTPException(status_code=404, detail="job not found")
    return manager.files(job_id)


@app.get("/api/jobs/{job_id}/files/{name}")
def job_file(job_id: str, name: str) -> FileResponse:
    path = manager.file_path(job_id, name)
    if path is None:
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path, media_type="text/plain", filename=name)


def _frontend_dist() -> Path | None:
    """Locate the built frontend so one server (and one origin) serves both
    the UI and the API — the layout the desktop shell relies on. In dev, the
    Vite server proxies /api instead and this mount is absent."""
    env = os.environ.get("OQP_STUDIO_FRONTEND")
    candidates = [Path(env)] if env else []
    bundle_dir = getattr(sys, "_MEIPASS", None)  # PyInstaller-frozen backend
    if bundle_dir:
        candidates.append(Path(bundle_dir) / "frontend_dist")
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    return next((p for p in candidates if (p / "index.html").is_file()), None)


_dist = _frontend_dist()
if _dist is not None:
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
