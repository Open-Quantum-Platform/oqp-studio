"""PATH repair for a GUI-launched app.

An app started from Finder or the Dock inherits launchd's minimal PATH, not
the one a terminal gets from the login shell. Homebrew on Apple Silicon
installs into /opt/homebrew/bin, which is absent from that minimal PATH, so a
perfectly good `openqp` on the machine looks missing to the app while working
fine in Terminal. The same applies to pipx and user installs.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Where package managers put executables, in the order they should be tried.
COMMON_BIN_DIRS = (
    "/opt/homebrew/bin",        # Homebrew, Apple Silicon
    "/usr/local/bin",           # Homebrew, Intel; most manual installs
    "/opt/local/bin",           # MacPorts
    "~/.local/bin",             # pip --user, pipx
    "~/bin",
    "/usr/bin",
    "/bin",
)


def _login_shell_path() -> str:
    """The PATH a login shell would produce, or an empty string.

    This is what makes a conda or pyenv installation visible: those live in
    directories only the user's shell profile knows about.
    """
    shell = os.environ.get("SHELL")
    if not shell or not Path(shell).exists():
        return ""
    try:
        result = subprocess.run(
            [shell, "-l", "-c", "printf %s \"$PATH\""],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def enrich_path() -> str:
    """Extend PATH with the login shell's and the usual install directories."""
    if os.name == "nt":
        return os.environ.get("PATH", "")

    entries: list[str] = []
    seen: set[str] = set()

    def add(directory: str) -> None:
        resolved = os.path.expanduser(directory)
        if resolved and resolved not in seen and Path(resolved).is_dir():
            seen.add(resolved)
            entries.append(resolved)

    for directory in os.environ.get("PATH", "").split(os.pathsep):
        add(directory)
    for directory in _login_shell_path().split(os.pathsep):
        add(directory)
    for directory in COMMON_BIN_DIRS:
        add(directory)

    os.environ["PATH"] = os.pathsep.join(entries)
    return os.environ["PATH"]


def locate(command: str) -> str | None:
    """Absolute path of `command`, so the UI can show what it found."""
    return shutil.which(command)


def describe() -> dict:
    """Diagnostics for the settings dialog."""
    return {
        "platform": sys.platform,
        "path_entries": os.environ.get("PATH", "").split(os.pathsep),
        "openqp": locate(os.environ.get("OQP_COMMAND", "openqp")),
    }
