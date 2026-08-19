from __future__ import annotations

import os
import shutil
from pathlib import Path

from .base import Runner


class LocalRunner(Runner):
    """Runs the native OpenQP installation found on PATH (or $OQP_COMMAND).

    Prefers the `openqp` console entry point installed by pyoqp. A later
    iteration will import pyoqp in-process for live callbacks instead of
    shelling out.
    """

    name = "local"

    @property
    def command(self) -> str:
        return os.environ.get("OQP_COMMAND", "openqp")

    def is_available(self) -> bool:
        return shutil.which(self.command) is not None

    def build_command(self, input_file: Path) -> list[str]:
        return [self.command, str(input_file)]
