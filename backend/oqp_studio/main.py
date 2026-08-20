from __future__ import annotations

import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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


PUBCHEM_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/SDF?record_type=3d"
)


def _parse_sdf_atoms(sdf: str) -> list[list]:
    """Atom list [[symbol, x, y, z], ...] from a V2000 SDF counts+atom block."""
    lines = sdf.splitlines()
    if len(lines) < 4:
        raise ValueError("SDF too short")
    natoms = int(lines[3][0:3])
    atoms = []
    for line in lines[4 : 4 + natoms]:
        x, y, z, symbol = float(line[0:10]), float(line[10:20]), float(line[20:30]), line[31:34]
        atoms.append([symbol.strip(), x, y, z])
    return atoms


@app.get("/api/pubchem/{name}")
def pubchem_lookup(name: str) -> dict:
    """Fetch a 3D structure from PubChem by compound name."""
    url = PUBCHEM_URL.format(name=urllib.parse.quote(name))
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            sdf = response.read().decode()
    except urllib.error.HTTPError as exc:
        detail = f"PubChem has no 3D record for '{name}'" if exc.code == 404 else str(exc)
        raise HTTPException(status_code=404, detail=detail) from exc
    except OSError as exc:
        raise HTTPException(status_code=502, detail=f"PubChem unreachable: {exc}") from exc
    try:
        atoms = _parse_sdf_atoms(sdf)
    except (ValueError, IndexError) as exc:
        raise HTTPException(status_code=502, detail="could not parse PubChem SDF") from exc
    return {"name": name, "atoms": atoms}


# In-memory store of geometry previews served back to the 3D viewer.
_previews: OrderedDict[str, str] = OrderedDict()


class PreviewRequest(BaseModel):
    xyz: str


@app.post("/api/preview")
def create_preview(req: PreviewRequest) -> dict:
    preview_id = uuid.uuid4().hex[:12]
    _previews[preview_id] = req.xyz
    while len(_previews) > 50:
        _previews.popitem(last=False)
    return {"url": f"/api/preview/{preview_id}.xyz"}


@app.get("/api/preview/{name}")
def get_preview(name: str) -> PlainTextResponse:
    preview = _previews.get(name.removesuffix(".xyz"))
    if preview is None:
        raise HTTPException(status_code=404, detail="preview not found")
    return PlainTextResponse(preview)


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
