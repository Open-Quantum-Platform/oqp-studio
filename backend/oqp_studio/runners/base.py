from __future__ import annotations

import abc
import subprocess
from pathlib import Path


class RunnerUnavailable(RuntimeError):
    """Raised when a runner cannot execute on this machine."""


class Runner(abc.ABC):
    """Runs OpenQP on a prepared job directory and streams output to job.log."""

    name: str = "abstract"

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Whether this runner can execute OpenQP on this machine."""

    @abc.abstractmethod
    def build_command(self, input_file: Path) -> list[str]:
        """Command line that runs OpenQP on `input_file`."""

    def run(self, job_dir: Path) -> int:
        """Blocking execution; the job manager calls this from a worker thread."""
        if not self.is_available():
            raise RunnerUnavailable(f"runner '{self.name}' is not available on this machine")
        input_file = next(
            (f for name in ("input.oqp", "input.inp") if (f := job_dir / name).exists()),
            job_dir / "input.oqp",
        )
        log_file = job_dir / "job.log"
        with log_file.open("ab") as log:
            proc = subprocess.Popen(
                self.build_command(input_file),
                cwd=job_dir,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            return proc.wait()
