from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from .runners import get_runner

JOBS_ROOT = Path("jobs_data")


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class JobRequest(BaseModel):
    input_text: str
    runner: str = "local"
    name: str = "job"


class JobInfo(BaseModel):
    id: str
    name: str
    status: JobStatus
    runner: str
    created_at: str
    exit_code: int | None = None
    error: str | None = None


class JobManager:
    """Minimal in-memory job queue: one worker thread per job (Phase 0).

    Phase 1 replaces this with a persistent queue with concurrency limits,
    kill/requeue, and WebSocket progress events.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, JobInfo] = {}
        self._lock = threading.Lock()

    def submit(self, req: JobRequest) -> JobInfo:
        job_id = uuid.uuid4().hex[:12]
        job_dir = JOBS_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "input.oqp").write_text(req.input_text)
        info = JobInfo(
            id=job_id,
            name=req.name,
            status=JobStatus.queued,
            runner=req.runner,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._jobs[job_id] = info
        threading.Thread(target=self._run, args=(job_id,), daemon=True).start()
        return info

    def _run(self, job_id: str) -> None:
        info = self._jobs[job_id]
        info.status = JobStatus.running
        try:
            exit_code = get_runner(info.runner).run(JOBS_ROOT / job_id)
            info.exit_code = exit_code
            info.status = JobStatus.done if exit_code == 0 else JobStatus.failed
        except Exception as exc:  # noqa: BLE001 — any failure must land in the job record
            info.error = str(exc)
            info.status = JobStatus.failed

    def get(self, job_id: str) -> JobInfo | None:
        return self._jobs.get(job_id)

    def list(self) -> list[JobInfo]:
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def log_tail(self, job_id: str, max_bytes: int = 65536) -> str:
        log_file = JOBS_ROOT / job_id / "job.log"
        if not log_file.exists():
            return ""
        data = log_file.read_bytes()
        return data[-max_bytes:].decode(errors="replace")


manager = JobManager()
