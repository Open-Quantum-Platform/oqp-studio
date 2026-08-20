"""Install and locate the standalone OpenQP compute engine.

The release carries an archive of the engine for each platform — unzip and
run, with no Python, compiler or BLAS on the user's machine. This module
downloads the one that matches, unpacks it beside the app's settings, and
tells the runners where it went, so a fresh install can compute without the
user assembling a toolchain first.

The same archive is a standalone command-line program: anyone who prefers a
terminal can download it from the release page and run ./openqp directly,
which is why it is published as its own asset rather than hidden inside the
installer.
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from . import network

EXECUTABLE = "openqp.exe" if os.name == "nt" else "openqp"


def data_dir() -> Path:
    """Where the engine is unpacked: beside the app's own settings."""
    return network.settings_path().parent / "engine"


def archive_suffix() -> str | None:
    """The release asset that matches this machine."""
    machine = platform.machine().lower()
    if sys.platform == "darwin":
        return "macos-arm64.zip" if machine in ("arm64", "aarch64") else "macos-x86_64.zip"
    if os.name == "nt":
        return "windows-x86_64.zip"
    if sys.platform.startswith("linux"):
        return "linux-aarch64.tar.gz" if machine in ("aarch64", "arm64") else "linux-x86_64.tar.gz"
    return None


def pick_asset(assets: list[dict]) -> dict | None:
    suffix = archive_suffix()
    if not suffix:
        return None
    for asset in assets:
        name = str(asset.get("name", ""))
        if name.startswith("openqp-") and name.endswith(suffix):
            return asset
    return None


# Where an engine may already be, in the order worth trying: the copy this
# app installed, then the places a user unpacks an archive by hand.
def search_paths() -> list[Path]:
    candidates = [data_dir()]
    home = Path.home()
    candidates += [
        home / "openqp",
        home / "Applications" / "openqp",
        home / ".local" / "share" / "openqp",
        Path("/opt/openqp"),
        Path("/usr/local/openqp"),
    ]
    return candidates


def locate() -> str | None:
    """An engine executable this machine can run, or None.

    PATH wins: a user who installed OpenQP themselves means that one.
    """
    from . import environment

    on_path = environment.locate(os.environ.get("OQP_COMMAND", "openqp"))
    if on_path:
        return on_path
    for directory in search_paths():
        candidate = directory / EXECUTABLE
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def status() -> dict:
    found = locate()
    return {
        "installed": bool(found),
        "path": found,
        "install_dir": str(data_dir()),
        "archive": archive_suffix(),
        "supported": archive_suffix() is not None,
    }


def _strip_single_root(target: Path) -> None:
    """Flatten an archive that unpacked into one wrapper directory.

    The wrapper is called openqp and so is the executable inside it, so the
    contents cannot be moved up in place — the first move would land on the
    wrapper itself. The wrapper is moved aside first.
    """
    entries = [path for path in target.iterdir() if path.name != "__MACOSX"]
    if len(entries) != 1 or not entries[0].is_dir():
        return
    staging = target.parent / f"{target.name}.unpack"
    if staging.exists():
        shutil.rmtree(staging)
    entries[0].rename(staging)
    for path in list(staging.iterdir()):
        shutil.move(str(path), str(target / path.name))
    staging.rmdir()


def install(url: str, progress=None) -> str:
    """Download and unpack the engine archive; returns the executable path."""
    target = data_dir()
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    suffix = ".zip" if url.endswith(".zip") else ".tar.gz"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        archive = Path(handle.name)
    with urllib.request.urlopen(url, timeout=300, context=network.context()) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with archive.open("wb") as out:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)

    if suffix == ".zip":
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(target)
    else:
        with tarfile.open(archive) as tarred:
            tarred.extractall(target)
    archive.unlink(missing_ok=True)
    _strip_single_root(target)

    executable = target / EXECUTABLE
    if not executable.is_file():
        raise RuntimeError(f"the archive contained no {EXECUTABLE}")
    # Zip archives do not carry the executable bit on every platform.
    executable.chmod(executable.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    if sys.platform == "darwin":
        # Downloaded archives are quarantined; the engine is unsigned.
        import subprocess

        subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(target)],
                       check=False, capture_output=True)
    return str(executable)
