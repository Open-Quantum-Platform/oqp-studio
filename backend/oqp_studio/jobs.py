from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

from .runners import get_runner

# Absolute, and overridable, so a job directory means the same thing however
# the server was launched — the desktop app starts it from an arbitrary cwd.
JOBS_ROOT = Path(os.environ.get("OQP_STUDIO_JOBS", "jobs_data")).resolve()


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
        self._recover()

    def _recover(self) -> None:
        """Adopt job directories left by earlier runs.

        Outputs outlive the process, so a restart should not empty the job
        list and leave the analysis tab with nothing to open.
        """
        if not JOBS_ROOT.is_dir():
            return
        for job_dir in sorted(JOBS_ROOT.iterdir()):
            if not job_dir.is_dir() or not any(job_dir.iterdir()):
                continue
            created = datetime.fromtimestamp(
                job_dir.stat().st_mtime, timezone.utc).isoformat()
            self._jobs[job_dir.name] = JobInfo(
                id=job_dir.name,
                name=job_dir.name,
                status=JobStatus.done,
                runner="recovered",
                created_at=created,
            )

    def submit(self, req: JobRequest) -> JobInfo:
        job_id = uuid.uuid4().hex[:12]
        job_dir = JOBS_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        # Sectioned legacy input starts with a [section]; otherwise .oqp route style.
        input_name = "input.inp" if req.input_text.lstrip().startswith("[") else "input.oqp"
        (job_dir / input_name).write_text(req.input_text)
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

    def adopt(self, name: str, files: list[tuple[str, bytes]]) -> JobInfo:
        """Register result files computed elsewhere as a job of their own.

        Analysis is built entirely on top of a job directory, so a run made
        on a cluster, by the command-line engine or by an earlier version of
        this app becomes analysable simply by giving its output files a job
        directory of their own -- summaries, spectra, orbitals, normal modes
        and property maps then work on it unchanged.
        """
        job_id = uuid.uuid4().hex[:12]
        job_dir = JOBS_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        written = 0
        for raw_name, data in files:
            # Browsers send a path when a whole folder is picked; only the
            # file name may reach the job directory.
            safe = Path(raw_name.replace("\\", "/")).name
            if not safe or safe.startswith("."):
                continue
            (job_dir / safe).write_bytes(data)
            written += 1
        if not written:
            job_dir.rmdir()
            raise ValueError("no usable files were given")
        info = JobInfo(
            id=job_id,
            name=name or "imported",
            status=JobStatus.done,
            runner="imported",
            created_at=datetime.now(timezone.utc).isoformat(),
            exit_code=0,
        )
        with self._lock:
            self._jobs[job_id] = info
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

    def files(self, job_id: str) -> list[dict]:
        job_dir = JOBS_ROOT / job_id
        if not job_dir.is_dir():
            return []
        return sorted(
            (
                {"name": p.name, "size": p.stat().st_size}
                for p in job_dir.iterdir()
                if p.is_file()
            ),
            key=lambda f: f["name"],
        )

    def file_path(self, job_id: str, name: str) -> Path | None:
        """Resolve a job output file, refusing path escapes."""
        job_dir = (JOBS_ROOT / job_id).resolve()
        candidate = (job_dir / name).resolve()
        if candidate.parent != job_dir or not candidate.is_file():
            return None
        return candidate

    def log_tail(self, job_id: str, max_bytes: int = 65536) -> str:
        log_file = JOBS_ROOT / job_id / "job.log"
        if not log_file.exists():
            return ""
        data = log_file.read_bytes()
        return data[-max_bytes:].decode(errors="replace")


manager = JobManager()
