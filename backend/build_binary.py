"""Build the PyInstaller-frozen backend binary for the Tauri sidecar.

Run from backend/ with the frontend already built (frontend/dist present):

    pip install -e . pyinstaller
    python build_binary.py

Writes dist/oqp-studio-backend[.exe] bundling the server and the built
frontend so the single binary serves UI + viewer + API from one origin.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    backend = Path(__file__).resolve().parent
    frontend_dist = backend.parent / "frontend" / "dist"
    if not (frontend_dist / "index.html").is_file():
        print("frontend/dist not found — run `npm run build` in frontend/ first.")
        return 1

    sep = ";" if os.name == "nt" else ":"
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--name",
        "oqp-studio-backend",
        "--add-data",
        f"{frontend_dist}{sep}frontend_dist",
        # uvicorn loads its loop/protocol classes by string name at runtime.
        "--hidden-import",
        "uvicorn.logging",
        "--collect-submodules",
        "uvicorn",
        str(backend / "oqp_studio" / "server_main.py"),
    ]
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=backend)


if __name__ == "__main__":
    raise SystemExit(main())
