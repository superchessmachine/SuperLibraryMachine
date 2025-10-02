"""Minimal macOS desktop shell that wraps the local Flask app in a WebView."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path

import webview

ROOT = Path(__file__).resolve().parents[1]
for candidate in {ROOT, ROOT / "web"}:
    path_str = str(candidate)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from web.app import app


HOST = os.getenv("SLM_HOST", "127.0.0.1")
PORT = int(os.getenv("SLM_PORT", "7860"))


def _run_server() -> None:
    # Use Werkzeug's reloader only when this module runs directly so the
    # background thread stays alive.
    app.run(host=HOST, port=PORT, use_reloader=False)


def main() -> None:
    server = threading.Thread(target=_run_server, daemon=True)
    server.start()

    # Allow the server to come up before trying to render the page.
    time.sleep(1.0)

    window_url = f"http://{HOST}:{PORT}"
    webview.create_window("SuperLibraryMachine", window_url)
    webview.start()


if __name__ == "__main__":
    main()
