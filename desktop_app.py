"""바른자세 데스크톱 셸: 메인 창 + 트레이."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn
from PIL import Image, ImageDraw

from backend import desktop_bridge

HOST = "127.0.0.1"
PORT = 8000


def _post(path: str) -> None:
    req = urllib.request.Request(f"http://{HOST}:{PORT}{path}", method="POST", data=b"")
    try:
        urllib.request.urlopen(req, timeout=3)
    except (urllib.error.URLError, TimeoutError, OSError):
        pass


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _wait_ready(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_open(HOST, PORT):
            return True
        time.sleep(0.2)
    return False


def _kill_listeners(port: int) -> None:
    try:
        out = subprocess.check_output(["netstat", "-ano", "-p", "tcp"], text=True, errors="ignore")
    except Exception:
        return
    pids = set()
    token = f":{port}"
    for line in out.splitlines():
        if "LISTENING" not in line.upper():
            continue
        if token not in line:
            continue
        pid = line.split()[-1]
        if pid.isdigit() and int(pid) != os.getpid():
            pids.add(pid)
    for pid in pids:
        subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)


def _tray_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 4, 56, 28), fill=(13, 165, 115, 255))
    d.polygon([(32, 22), (48, 58), (16, 58)], fill=(13, 159, 110, 255))
    return img


def main():
    try:
        import webview
        import pystray
    except ImportError:
        print("pip install pywebview pystray")
        sys.exit(1)

    server: uvicorn.Server | None = None
    if _port_open(HOST, PORT):
        print("[바른자세] 이전 서버를 종료하고 지금 코드로 다시 시작합니다.", flush=True)
        _post("/api/desktop/shutdown")
        deadline = time.time() + 6.0
        while time.time() < deadline and _port_open(HOST, PORT):
            time.sleep(0.2)
        if _port_open(HOST, PORT):
            _kill_listeners(PORT)

    config = uvicorn.Config(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )
    server = uvicorn.Server(config)

    def _run():
        server.run()

    threading.Thread(target=_run, daemon=True, name="uvicorn").start()
    if not _wait_ready():
        print("서버를 시작하지 못했습니다.")
        sys.exit(1)

    from backend.desktop_overlay import overlay as desktop_overlay

    desktop_overlay.start()
    _post("/api/measure/stop")

    # 개발 중 Vite가 켜져 있으면 최신 UI, 아니면 FastAPI가 서빙하는 dist
    if _port_open(HOST, 5173):
        url = f"http://{HOST}:5173"
    else:
        url = f"http://{HOST}:{PORT}"

    holder: dict = {"window": None, "icon": None, "exiting": False}

    class Api:
        def minimize(self):
            w = holder["window"]
            if w is not None:
                w.hide()

    def restore():
        w = holder["window"]
        if w is not None:
            w.show()
            try:
                w.restore()
            except Exception:
                pass

    def quit_app(icon=None, _item=None):
        if holder.get("exiting"):
            return
        holder["exiting"] = True
        _post("/api/desktop/shutdown")
        ic = holder.get("icon")
        if ic is not None:
            try:
                ic.stop()
            except Exception:
                pass
        if server is not None:
            server.should_exit = True
        w = holder.get("window")
        if w is not None:
            try:
                w.destroy()
            except Exception:
                pass
        try:
            webview.windows.clear()
        except Exception:
            pass
        os._exit(0)

    desktop_bridge.minimize_cb = lambda: Api().minimize()
    desktop_bridge.restore_cb = restore
    desktop_bridge.quit_cb = lambda: quit_app()

    window = webview.create_window(
        "바른자세",
        url,
        width=1280,
        height=800,
        js_api=Api(),
        min_size=(1100, 700),
    )
    holder["window"] = window

    def on_closing():
        quit_app()
        return True

    window.events.closing += on_closing

    def tray_run():
        menu = pystray.Menu(
            pystray.MenuItem("열기", lambda *_: restore(), default=True),
            pystray.MenuItem("종료", quit_app),
        )
        icon = pystray.Icon("바른자세", _tray_image(), "바른자세", menu)
        holder["icon"] = icon
        icon.run()

    threading.Thread(target=tray_run, daemon=True, name="tray").start()
    webview.start()
    quit_app()


if __name__ == "__main__":
    main()
