from __future__ import annotations

import os
import shutil
from pathlib import Path

from .base import Runner


class LocalRunner(Runner):
    """Runs the native OpenQP engine.

    Looks for it on PATH first — a user who installed OpenQP themselves means
    that one — and otherwise for a standalone engine archive, either the copy
    this app downloaded or one the user unpacked in a usual place. The
    archives are self-contained, so the one the app installs needs no Python
    or BLAS on the machine.
    """

    name = "local"

    @property
    def command(self) -> str:
        override = os.environ.get("OQP_COMMAND")
        if override:
            return override
        from .. import engine

        return engine.locate() or "openqp"

    def is_available(self) -> bool:
        command = self.command
        return shutil.which(command) is not None or Path(command).is_file()

    def build_command(self, input_file: Path) -> list[str]:
        return [self.command, str(input_file)]
