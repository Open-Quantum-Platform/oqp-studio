from __future__ import annotations

from fastapi import FastAPI, HTTPException

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
