"""바른자세 데스크톱 셸: 메인 창 + 트레이."""
from __future__ import annotations

import ctypes
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
try:
    os.chdir(ROOT)
except OSError:
    pass
_py_dir = Path(sys.executable).resolve().parent
_cv_dir = _py_dir / "Lib" / "site-packages" / "cv2"
_path_bits = [str(_py_dir), str(_py_dir / "DLLs")]
if _cv_dir.is_dir():
    _path_bits.append(str(_cv_dir))
os.environ["PATH"] = os.pathsep.join(_path_bits) + os.pathsep + os.environ.get("PATH", "")
if hasattr(os, "add_dll_directory"):
    for _d in _path_bits:
        if os.path.isdir(_d):
            try:
                os.add_dll_directory(_d)
            except OSError:
                pass
_ICON_FILE = ROOT / "baruna-assets" / "barun_jase.ico"
_APP_ID = "PostureApp.BarunJase"
_WV2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"


def _log_crash(message: str, exc: BaseException | None = None) -> None:
    try:
        log_dir = Path.home() / ".posture_app" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "app.log").open("a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " [ERROR] [desktop] " + message + "\n")
            if exc is not None:
                import traceback
                f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except Exception:
        pass


def _fatal(message: str, exc: BaseException | None = None) -> None:
    _log_crash(message, exc)
    try:
        ctypes.windll.user32.MessageBoxW(None, message, "바른자세", 0x00000010)
    except Exception:
        pass


def _webview2_installed() -> bool:
    if sys.platform != "win32":
        return True
    import winreg
    keys = (
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{_WV2_GUID}"),
        (winreg.HKEY_CURRENT_USER, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WV2_GUID}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WV2_GUID}"),
    )
    for root, path in keys:
        try:
            with winreg.OpenKey(root, path) as key:
                pv, _ = winreg.QueryValueEx(key, "pv")
            if pv and str(pv) not in ("", "0.0.0.0"):
                return True
        except OSError:
            continue
    return False


try:
    import uvicorn
    from PIL import Image, ImageDraw

    from backend import app_log, desktop_bridge
except Exception as _imp_err:
    _fatal(
        "바른자세를 시작하지 못했습니다.\n\n"
        "필수 구성 요소를 불러오지 못했습니다.\n"
        f"{_imp_err}\n\n"
        "설치 프로그램을 다시 실행하거나, 로그를 확인해 주세요.\n"
        f"로그: {Path.home() / '.posture_app' / 'logs' / 'app.log'}",
        _imp_err,
    )
    sys.exit(1)

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
    if _ICON_FILE.is_file():
        try:
            return Image.open(_ICON_FILE).convert("RGBA")
        except Exception:
            pass
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 4, 56, 28), fill=(13, 165, 115, 255))
    d.polygon([(32, 22), (48, 58), (16, 58)], fill=(13, 159, 110, 255))
    return img


def _center_xy(width: int, height: int) -> tuple[int, int]:
    """기본 모니터 작업 영역 중앙."""
    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    user32 = ctypes.windll.user32
    rc = RECT()
    if user32.SystemParametersInfoW(48, 0, ctypes.byref(rc), 0):
        ww, hh = rc.right - rc.left, rc.bottom - rc.top
        x = rc.left + max(0, (ww - width) // 2)
        y = rc.top + max(0, (hh - height) // 2)
        return int(x), int(y)
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    return max(0, (sw - width) // 2), max(0, (sh - height) // 2)


def _set_app_id() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(_APP_ID)
    except Exception:
        pass


def _apply_window_icon() -> None:
    if sys.platform != "win32" or not _ICON_FILE.is_file():
        return
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "바른자세")
    if not hwnd:
        return
    user32.LoadImageW.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    user32.LoadImageW.restype = wintypes.HANDLE
    IMAGE_ICON, LR_LOADFROMFILE, LR_DEFAULTSIZE = 1, 0x0010, 0x0040
    WM_SETICON, ICON_SMALL, ICON_BIG = 0x0080, 0, 1
    hicon = user32.LoadImageW(
        None, str(_ICON_FILE), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
    )
    if hicon:
        user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon)
        user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)


def main():
    _set_app_id()
    app_log.info(
        "desktop",
        "launch",
        executable=sys.executable,
        script=str(ROOT),
        frozen=getattr(sys, "frozen", False),
        pythonw="pythonw" in os.path.basename(sys.executable).lower(),
        webview2=_webview2_installed(),
    )
    dist = ROOT / "frontend" / "dist" / "index.html"
    if not dist.is_file():
        _fatal(
            "바른자세를 시작하지 못했습니다.\n\n"
            "화면 파일(frontend/dist)이 없습니다.\n"
            "설치가 손상된 경우 설치 프로그램을 다시 실행해 주세요."
        )
        sys.exit(1)
    if not _webview2_installed():
        _fatal(
            "바른자세를 시작하지 못했습니다.\n\n"
            "Microsoft Edge WebView2 Runtime이 설치되어 있지 않습니다.\n"
            "바른자세 설치 프로그램을 다시 실행하면 WebView2를 함께 설치합니다.\n"
            "오프라인 PC라면 설치 파일에 포함된 WebView2 설치 프로그램이 필요합니다."
        )
        sys.exit(1)
    try:
        import webview
        import pystray
    except ImportError as e:
        app_log.exception("desktop", "missing_deps", e)
        _fatal(
            "바른자세를 시작하지 못했습니다.\n\n"
            "pywebview 또는 pystray를 불러오지 못했습니다.\n"
            f"{e}",
            e,
        )
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
        _fatal(
            "바른자세를 시작하지 못했습니다.\n\n"
            "내부 서버(127.0.0.1:8000)가 준비되지 않았습니다.\n"
            "다른 프로그램이 8000 포트를 쓰는지 확인한 뒤 다시 실행해 주세요.\n"
            f"로그: {Path.home() / '.posture_app' / 'logs' / 'app.log'}"
        )
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

    win_w, win_h = 1280, 800
    cx, cy = _center_xy(win_w, win_h)
    window = webview.create_window(
        "바른자세",
        url,
        width=win_w,
        height=win_h,
        x=cx,
        y=cy,
        js_api=Api(),
        min_size=(1100, 700),
    )
    holder["window"] = window

    def on_closing():
        quit_app()
        return True

    def on_shown():
        _apply_window_icon()

    window.events.closing += on_closing
    try:
        window.events.shown += on_shown
    except Exception:
        pass

    def tray_run():
        menu = pystray.Menu(
            pystray.MenuItem("열기", lambda *_: restore(), default=True),
            pystray.MenuItem("종료", quit_app),
        )
        icon = pystray.Icon("바른자세", _tray_image(), "바른자세", menu)
        holder["icon"] = icon
        icon.run()

    threading.Thread(target=tray_run, daemon=True, name="tray").start()
    try:
        webview.start(gui="edgechromium")
    except Exception as e:
        _fatal(
            "바른자세 창을 열지 못했습니다.\n\n"
            "Microsoft Edge WebView2 Runtime을 확인한 뒤 다시 실행해 주세요.\n"
            f"{e}\n\n"
            f"로그: {Path.home() / '.posture_app' / 'logs' / 'app.log'}",
            e,
        )
        sys.exit(1)
    quit_app()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        _fatal(
            "바른자세를 시작하지 못했습니다.\n\n"
            f"{e}\n\n"
            f"로그: {Path.home() / '.posture_app' / 'logs' / 'app.log'}",
            e,
        )
        sys.exit(1)
