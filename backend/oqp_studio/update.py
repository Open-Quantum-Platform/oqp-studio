"""One-click update: download the right installer and swap the app in place.

macOS gets a real in-place update, because the release ships the .app as a
tarball: the new copy is staged, a detached script waits for this app to quit,
replaces /Applications/OQP Studio.app and relaunches it. Windows and Linux
download their installer and hand it to the system, which is as far as an
unprivileged process can take it there.
"""

from __future__ import annotations

import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from . import network

APP_NAME = "OQP Studio"


def asset_suffix() -> str | None:
    """The release asset this machine should install."""
    if sys.platform == "darwin":
        return ("macos-apple-silicon.app.tar.gz" if platform.machine() == "arm64"
                else "macos-intel.app.tar.gz")
    if os.name == "nt":
        return "windows-x64-setup.exe"
    if sys.platform.startswith("linux"):
        return "linux-x86_64.AppImage"
    return None


def pick_asset(assets: list[dict]) -> dict | None:
    suffix = asset_suffix()
    if not suffix:
        return None
    for asset in assets:
        if str(asset.get("name", "")).endswith(suffix):
            return asset
    return None


def download(url: str, target: Path, progress=None) -> Path:
    """Fetch `url` into `target`, reporting bytes as they arrive."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120, context=network.context()) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with target.open("wb") as handle:
            while True:
                chunk = response.read(1 << 16)
                if not chunk:
                    break
                handle.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    return target


def installed_app_path() -> Path | None:
    """Where this .app lives, when running as a macOS bundle."""
    if sys.platform != "darwin":
        return None
    # The frozen sidecar sits inside Contents/MacOS of the bundle.
    for parent in Path(sys.executable).resolve().parents:
        if parent.suffix == ".app":
            return parent
    candidate = Path(f"/Applications/{APP_NAME}.app")
    return candidate if candidate.exists() else None


SWAP_SCRIPT = """#!/bin/sh
# Replace the running app once it has quit, then start the new one.
set -e
target="$1"
staged="$2"
for _ in $(seq 1 30); do
    pgrep -x "{app}" >/dev/null || break
    sleep 1
done
if pgrep -x "{app}" >/dev/null; then
    osascript -e 'quit app "{app}"' >/dev/null 2>&1 || true
    sleep 3
fi
rm -rf "$target"
mv "$staged" "$target"
xattr -dr com.apple.quarantine "$target" >/dev/null 2>&1 || true
open "$target"
"""


def install_macos(tarball: Path, progress=None) -> str:
    """Stage the new .app and schedule the swap for when this one quits."""
    target = installed_app_path()
    if target is None:
        raise RuntimeError("could not locate the installed application bundle")
    staging = Path(tempfile.mkdtemp(prefix="oqp-studio-update-"))
    if progress:
        progress("unpacking the new version")
    with tarfile.open(tarball) as archive:
        archive.extractall(staging)
    staged = next((path for path in staging.iterdir() if path.suffix == ".app"), None)
    if staged is None:
        raise RuntimeError("the downloaded archive contained no application")

    script = staging / "swap.sh"
    script.write_text(SWAP_SCRIPT.format(app=APP_NAME))
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    # Detached, so it outlives the app it is about to replace.
    subprocess.Popen(
        [str(script), str(target), str(staged)],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return f"{target} will be replaced as soon as the app quits"


def install_elsewhere(installer: Path) -> str:
    """Hand the downloaded installer to the system."""
    if os.name == "nt":
        os.startfile(str(installer))  # noqa: S606 — the user asked to install
        return f"the installer {installer.name} was started"
    installer.chmod(installer.stat().st_mode | stat.S_IEXEC)
    opener = shutil.which("xdg-open")
    if opener:
        subprocess.Popen([opener, str(installer.parent)], start_new_session=True)
    return f"{installer} is ready to run"
