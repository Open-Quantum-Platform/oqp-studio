"""Standalone server entry point — used by the PyInstaller-frozen backend.

The Tauri shell spawns this binary as a sidecar:
    oqp-studio-backend --port 8814
"""

from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description="OQP Studio backend server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("OQP_STUDIO_PORT", "8814")),
    )
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    import uvicorn

    from oqp_studio.main import app

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
