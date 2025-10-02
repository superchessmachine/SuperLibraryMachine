"""macOS desktop shell that wraps the local Flask app in a WebView."""

from __future__ import annotations

import html
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import webview

if hasattr(sys, "_MEIPASS"):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parents[1]

for candidate in (ROOT, ROOT / "web"):
    path_str = str(candidate)
    if path_str not in sys.path and Path(path_str).exists():
        sys.path.insert(0, path_str)

from web.app import app
from web.rag_server import reset_openai_client


ENV_FILE = ROOT / "mac_app" / ".env"
APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "SuperLibraryMachine"
CONFIG_PATH = APP_SUPPORT_DIR / "config.json"

HOST = os.getenv("SLM_HOST", "127.0.0.1")
PORT = int(os.getenv("SLM_PORT", "7860"))

SUPPORTS_MENU = all(
    hasattr(webview, attr) for attr in ("Menu", "MenuAction", "MenuSeparator")
)


def _load_local_env() -> None:
    if not ENV_FILE.exists():
        return
    for raw_line in ENV_FILE.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _persist_config(data: dict) -> None:
    APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def _set_runtime_api_key(key: str, persist: bool = True) -> None:
    key = key.strip()
    os.environ["OPENAI_API_KEY"] = key
    if persist:
        data = _load_config()
        data["openai_api_key"] = key
        _persist_config(data)
    reset_openai_client()


def _get_saved_api_key() -> Optional[str]:
    return _load_config().get("openai_api_key")


SETTINGS_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>SuperLibraryMachine &ndash; Settings</title>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background-color: #f3f4f6;
        color: #1f2933;
        margin: 0;
        padding: 24px;
      }}
      h1 {{ margin-top: 0; font-size: 1.4rem; }}
      label {{ display: block; margin-bottom: 8px; font-weight: 600; }}
      input {{
        width: 100%;
        padding: 10px;
        font-size: 1rem;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        box-sizing: border-box;
      }}
      .hint {{
        font-size: 0.85rem;
        color: #64748b;
        margin-top: 8px;
      }}
      .actions {{
        margin-top: 20px;
        display: flex;
        gap: 12px;
      }}
      button {{
        background: #2563eb;
        border: none;
        color: #fff;
        padding: 10px 18px;
        border-radius: 6px;
        font-size: 1rem;
        cursor: pointer;
      }}
      button.secondary {{
        background: transparent;
        color: #2563eb;
        border: 1px solid #2563eb;
      }}
      .error {{
        color: #dc2626;
        margin-top: 12px;
        font-size: 0.9rem;
        min-height: 18px;
      }}
      .success {{
        color: #16a34a;
        margin-top: 12px;
        font-size: 0.9rem;
        min-height: 18px;
      }}
    </style>
  </head>
  <body>
    <h1>OpenAI API Key</h1>
    <form id="keyForm">
      <label for="apiKey">Paste your key:</label>
      <input type="password" id="apiKey" autocomplete="off" value="{prefill}" />
      <p class="hint">Stored locally at {config_path} for future launches.</p>
      <div class="actions">
        <button type="submit">Save &amp; Continue</button>
        <button type="button" class="secondary" id="cancelBtn" style="{cancel_style}">Cancel</button>
      </div>
      <p class="error" id="error"></p>
      <p class="success" id="success"></p>
    </form>
    <script>
      const form = document.getElementById('keyForm');
      const input = document.getElementById('apiKey');
      const errorEl = document.getElementById('error');
      const successEl = document.getElementById('success');
      document.getElementById('cancelBtn').addEventListener('click', () => {{
        window.close();
      }});
      form.addEventListener('submit', async (event) => {{
        event.preventDefault();
        errorEl.textContent = '';
        successEl.textContent = '';
        const key = input.value.trim();
        try {{
          const result = await window.pywebview.api.save_key(key);
          if (result.ok) {{
            successEl.textContent = 'Key saved.';
            setTimeout(() => window.close(), 400);
          }} else {{
            errorEl.textContent = result.error || 'Unable to save key.';
          }}
        }} catch (err) {{
          errorEl.textContent = err.message || String(err);
        }}
      }});
    </script>
  </body>
</html>
"""

SETTINGS_BUTTON_JS = """
(function() {
  if (window.__slmSettingsButtonInitialized) { return; }
  window.__slmSettingsButtonInitialized = true;
  const btn = document.createElement('button');
  btn.id = '__slm_settings_button';
  btn.textContent = 'Settings';
  btn.style.position = 'fixed';
  btn.style.top = '16px';
  btn.style.right = '16px';
  btn.style.zIndex = '2147483647';
  btn.style.padding = '8px 14px';
  btn.style.background = '#2563eb';
  btn.style.color = '#fff';
  btn.style.border = 'none';
  btn.style.borderRadius = '18px';
  btn.style.fontFamily = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
  btn.style.fontSize = '14px';
  btn.style.cursor = 'pointer';
  btn.style.boxShadow = '0 4px 12px rgba(37, 99, 235, 0.3)';
  btn.onmouseenter = function() { btn.style.filter = 'brightness(1.05)'; };
  btn.onmouseleave = function() { btn.style.filter = 'brightness(1.0)'; };
  btn.onclick = function() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.open_settings) {
      window.pywebview.api.open_settings();
    } else {
      alert('Settings bridge unavailable.');
    }
  };
  document.body.appendChild(btn);
})();
"""


def _render_settings_html(initial_key: str, *, allow_cancel: bool) -> str:
    return SETTINGS_HTML.format(
        prefill=html.escape(initial_key or ""),
        config_path=html.escape(str(CONFIG_PATH)),
        cancel_style="display:inline-block;" if allow_cancel else "display:none;",
    )


class SettingsBridge:
    def __init__(self, on_saved: Callable[[str], None]):
        self.on_saved = on_saved
        self.saved_key: Optional[str] = None

    def save_key(self, key: str) -> dict:
        key = (key or "").strip()
        if not key:
            return {"ok": False, "error": "API key cannot be empty."}
        self.on_saved(key)
        self.saved_key = key
        return {"ok": True}


class AppBridge:
    def __init__(self):
        self.window: Optional[webview.Window] = None

    def attach(self, window: webview.Window) -> None:
        self.window = window

    def open_settings(self) -> None:
        target = self.window or (webview.windows[0] if webview.windows else None)
        _open_settings_menu(target)


def _show_settings_window(initial_key: str, *, blocking: bool, parent: Optional[webview.Window] = None) -> Optional[str]:
    if not blocking:
        raise RuntimeError("Non-blocking settings window is not supported in this mode.")

    captured: dict[str, Optional[str]] = {"key": None}

    def handle_saved(key: str) -> None:
        _set_runtime_api_key(key, persist=True)
        captured["key"] = key

    bridge = SettingsBridge(handle_saved)
    allow_cancel = bool(initial_key)

    window = webview.create_window(
        "SuperLibraryMachine – Settings",
        html=_render_settings_html(initial_key, allow_cancel=allow_cancel),
        js_api=bridge,
        width=460,
        height=340,
        resizable=False,
        parent=parent,
    )
    setattr(window, "_bridge", bridge)
    webview.start()
    return captured["key"]


def _prompt_for_key(window: webview.Window, initial_key: str = "") -> bool:
    if window is None:
        return False

    default = json.dumps(initial_key or "")
    script = f"""
    (function() {{
        var value = window.prompt('Paste your OpenAI API key', {default});
        if (value === null) {{
            return '__SLM_CANCEL__';
        }}
        return value;
    }})()
    """
    try:
        result = window.evaluate_js(script)
    except Exception:
        return False

    if result in (None, '__SLM_CANCEL__'):
        return False

    key = str(result or "").strip()
    _set_runtime_api_key(key, persist=True)
    return bool(key)


def _ensure_api_key() -> bool:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        _set_runtime_api_key(env_key, persist=True)
        return True

    saved_key = _get_saved_api_key()
    if saved_key:
        os.environ.setdefault("OPENAI_API_KEY", saved_key)
        return True

    os.environ.setdefault("OPENAI_API_KEY", "")
    return False


def _open_settings_menu(window: Optional[webview.Window] = None) -> None:
    current = os.getenv("OPENAI_API_KEY") or _get_saved_api_key() or ""
    target = window or (webview.windows[0] if webview.windows else None)
    if target is None:
        _show_settings_window(current, blocking=True)
    else:
        _prompt_for_key(target, current)


def _build_menu() -> Optional[webview.Menu]:
    if not SUPPORTS_MENU:
        return None

    return webview.Menu(
        webview.MenuAction("Settings…", _open_settings_menu),
        webview.MenuSeparator(),
        webview.MenuAction("Quit", lambda window: window.destroy()),
    )


def _run_server() -> None:
    app.run(host=HOST, port=PORT, use_reloader=False)


def main() -> None:
    _load_local_env()

    has_key = _ensure_api_key()

    server = threading.Thread(target=_run_server, daemon=True)
    server.start()

    time.sleep(1.0)

    menu = _build_menu()
    window_url = f"http://{HOST}:{PORT}"

    app_bridge = AppBridge()
    js_api = None if SUPPORTS_MENU else app_bridge
    main_window = webview.create_window(
        "SuperLibraryMachine",
        window_url,
        menu=menu,
        js_api=js_api,
    )
    app_bridge.attach(main_window)

    def on_start() -> None:
        if not SUPPORTS_MENU:
            try:
                main_window.evaluate_js(SETTINGS_BUTTON_JS)
            except Exception:
                pass
        if not has_key:
            print("⚠️  No OpenAI API key configured. Use Settings to add one when ready.")

    webview.start(on_start)


if __name__ == "__main__":
    main()
