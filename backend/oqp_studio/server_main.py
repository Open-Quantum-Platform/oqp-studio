"""Standalone server entry point — used by the PyInstaller-frozen backend.

The Tauri shell spawns this binary as a sidecar:
    oqp-studio-backend --port 8814
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def log_path() -> Path:
    """Where a startup failure is recorded.

    Worked out here rather than by importing the app's own settings module,
    because the failure being recorded may be that module failing to import.
    """
    override = os.environ.get("OQP_STUDIO_CONFIG")
    if override:
        return Path(override).parent / "backend.log"
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "OQP Studio"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home())) / "OQP Studio"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME",
                                   Path.home() / ".config")) / "oqp-studio"
    return base / "backend.log"


def main() -> None:
    parser = argparse.ArgumentParser(description="OQP Studio backend server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("OQP_STUDIO_PORT", "8814")),
    )
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    try:
        import uvicorn

        from oqp_studio.main import app

        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except BaseException:
        # The shell can only see that the port never opened. Whatever went
        # wrong is written where it can be read afterwards -- guessing at a
        # sidecar's stack trace from "failed to start" is not debugging.
        import traceback

        report = traceback.format_exc()
        try:
            path = log_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report)
        except OSError:
            pass
        print(report, file=sys.stderr)
        raise


if __name__ == "__main__":
    main()
