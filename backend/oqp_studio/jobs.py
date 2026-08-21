from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from .input_files import SUPPORTED_INPUT_SUFFIXES, calculation_log, find_input_file
from .runners import get_runner


def _preferred_root() -> Path:
    from . import workspace

    return workspace.preferred()


# Worked out from the environment and the saved setting alone -- importing
# this module must not touch the disk. The directory is created, and any
# fallback chosen, the first time a job actually needs it.
JOBS_ROOT = _preferred_root()


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"


class JobRequest(BaseModel):
    input_text: str
    runner: str = "local"
    name: str = "job"
    input_name: str | None = None
    threads: int = Field(default=1, ge=1)


class JobInfo(BaseModel):
    id: str
    name: str
    status: JobStatus
    runner: str
    threads: int = 1
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
        self._ready = False

    def _ensure(self) -> Path:
        """Create the results directory, once, on the first job that needs it.

        Deliberately not done in __init__: this module is imported while the
        server is starting, and on macOS creating a directory in Documents
        waits for the user to grant permission -- which the shell, waiting
        thirty seconds for a port, reads as the backend failing to start.
        """
        global JOBS_ROOT

        if self._ready:
            return JOBS_ROOT
        from . import workspace

        JOBS_ROOT = workspace.ensure(JOBS_ROOT)
        self._ready = True
        self._recover()
        return JOBS_ROOT

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
        from . import host

        check = host.admission(req.input_text, req.threads)
        if not check["permitted"]:
            raise ValueError(
                f"RAM limit: estimated {check['estimated_memory_bytes'] / 1024**3:.1f} GiB, "
                f"available {check['memory_available_bytes'] / 1024**3:.1f} GiB. "
                "Choose a smaller calculation or free memory before running."
            )
        self._ensure()
        job_id = uuid.uuid4().hex[:12]
        job_dir = JOBS_ROOT / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        input_name = self._input_name(req)
        (job_dir / input_name).write_text(req.input_text)
        info = JobInfo(
            id=job_id,
            name=req.name,
            status=JobStatus.queued,
            runner=req.runner,
            threads=req.threads,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._jobs[job_id] = info
        threading.Thread(target=self._run, args=(job_id,), daemon=True).start()
        return info

    @staticmethod
    def _input_name(req: JobRequest) -> str:
        """Choose a default input name or validate the name supplied by the UI."""
        if not req.input_name or not req.input_name.strip():
            # Sectioned legacy input starts with a [section]; otherwise .oqp route style.
            return "input.inp" if req.input_text.lstrip().startswith("[") else "input.oqp"
        supplied = req.input_name.strip()
        name = Path(supplied).name
        if name != supplied or name.startswith(".") or name in {"", ".", ".."}:
            raise ValueError("input file name must not contain a path")
        if Path(name).suffix.lower() not in SUPPORTED_INPUT_SUFFIXES:
            raise ValueError("input file name must end in .oqp or .inp")
        return name

    def adopt(self, name: str, files: list[tuple[str, bytes]]) -> JobInfo:
        """Register result files computed elsewhere as a job of their own.

        Analysis is built entirely on top of a job directory, so a run made
        on a cluster, by the command-line engine or by an earlier version of
        this app becomes analysable simply by giving its output files a job
        directory of their own -- summaries, spectra, orbitals, normal modes
        and property maps then work on it unchanged.
        """
        self._ensure()
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
            exit_code = get_runner(info.runner).run(JOBS_ROOT / job_id, info.threads)
            info.exit_code = exit_code
            info.status = JobStatus.done if exit_code == 0 else JobStatus.failed
        except Exception as exc:  # noqa: BLE001 — any failure must land in the job record
            info.error = str(exc)
            info.status = JobStatus.failed

    def rebase(self) -> None:
        """Forget the old results directory and read the new one."""
        with self._lock:
            self._jobs.clear()
        self._recover()

    def busy(self) -> bool:
        return any(job.status in (JobStatus.queued, JobStatus.running)
                   for job in self._jobs.values())

    def get(self, job_id: str) -> JobInfo | None:
        return self._jobs.get(job_id)

    def list(self) -> list[JobInfo]:
        self._ensure()
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def files(self, job_id: str) -> list[dict]:
        self._ensure()
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
        job_dir = JOBS_ROOT / job_id
        # job.log is the runner process's stdout/stderr capture. OpenQP writes
        # its actual calculation record separately, so show that record when
        # it has appeared rather than the launcher transcript.
        input_file = find_input_file(job_dir)
        candidates = [calculation_log(input_file)]
        candidates.extend(
            sorted(
                path for suffix in ("*.log", "*.out")
                for path in job_dir.glob(suffix)
                if path not in {job_dir / "job.log", calculation_log(input_file)}
            )
        )
        candidates.append(job_dir / "job.log")
        log_file = next((path for path in candidates if path.is_file()), None)
        if log_file is None:
            return ""
        data = log_file.read_bytes()
        return data[-max_bytes:].decode(errors="replace")


manager = JobManager()


def set_root(directory: Path) -> Path:
    """Write results somewhere else from now on.

    A job already running keeps writing where it was told -- its runner has
    the old path -- which is why the API refuses to move while one is in
    flight rather than leaving its output stranded.
    """
    global JOBS_ROOT

    JOBS_ROOT = directory
    manager._ready = True
    manager.rebase()
    return JOBS_ROOT
