"""OQP Studio desktop launcher: own window, no browser needed.

Starts the FastAPI backend on a local port in a background thread, waits for
it to come up, then opens the UI in a native window via pywebview (Cocoa on
macOS, EdgeChromium/WebView2 on Windows, GTK or Qt on Linux). This is the
interim native experience until the Tauri shell ships installers.

Run with:  oqp-studio            (after `pip install -e ".[desktop]"`)
      or:  python -m oqp_studio.desktop
"""

from __future__ import annotations

import socket
import threading
import time
import urllib.request


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_health(url: str, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def main() -> int:
    try:
        import webview
    except ImportError:
        print("The desktop window needs pywebview. Install it with:")
        print('  pip install -e ".[desktop]"')
        print("or run the server directly and open it in a browser:")
        print("  uvicorn oqp_studio.main:app --port 8814")
        return 1

    import uvicorn

    from .main import app

    port = _free_port()
    url = f"http://127.0.0.1:{port}"

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()

    if not _wait_for_health(url):
        print("Backend failed to start.")
        return 1

    window = webview.create_window(
        "OQP Studio",
        url,
        width=1280,
        height=800,
        min_size=(900, 600),
        background_color="#16181d",
    )
    del window
    webview.start()

    server.should_exit = True
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
