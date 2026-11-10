"""Windows 데스크톱 위 원형 알림. 별도 프로세스 + 픽셀 알파(layered window)."""
from __future__ import annotations

import ctypes
import queue
import socket
import subprocess
import sys
import threading
import time
from ctypes import wintypes
from multiprocessing.connection import Client, Listener
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WARN = (255, 149, 32, 255)
DANGER = (236, 56, 56, 255)
HOLD_SEC = 3.0
SLIDE_SEC = 0.55
SCALE = 4
MAIN_D = 44
DOT_D = (9, 7, 5)
GAP = 6
PAD = 16
TOP_Y = 36

WIN_W = PAD * 2 + MAIN_D + GAP * 3 + sum(DOT_D)
WIN_H = PAD * 2 + MAIN_D

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040
ULW_ALPHA = 0x02
AC_SRC_OVER = 0x00
AC_SRC_ALPHA = 0x01
BI_RGB = 0


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def _ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _grade_key(label) -> int | None:
    if label == "주의":
        return 2
    if label == "부적정":
        return 3
    if label == "적정":
        return 1
    return None


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("malgunbd.ttf", "malgun.ttf"):
        path = Path(r"C:\Windows\Fonts") / name
        if path.is_file():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _soft_circle(size: int, fill) -> Image.Image:
    """4배 그린 뒤 줄여 가장자리가 부드러운 원."""
    s = SCALE
    big = Image.new("RGBA", (size * s, size * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    d.ellipse((1, 1, size * s - 2, size * s - 2), fill=fill)
    return big.resize((size, size), Image.Resampling.LANCZOS)


def _mix(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _orb_body(size: int, rgb: tuple[int, int, int, int]) -> Image.Image:
    s = SCALE
    n = size * s
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = rgb[:3]
    inner = (min(255, r + 36), min(255, g + 22), min(255, b + 12))
    outer = (max(0, int(r * 0.82)), max(0, int(g * 0.78)), max(0, int(b * 0.78)))
    steps = 28
    for i in range(steps, -1, -1):
        t = i / steps
        col = (
            _mix(inner[0], outer[0], t),
            _mix(inner[1], outer[1], t),
            _mix(inner[2], outer[2], t),
            255,
        )
        rad = int((n / 2 - 1) * (0.22 + 0.78 * t))
        ox = n // 2
        oy = int(n * (0.48 - 0.05 * (1 - t)))
        d.ellipse((ox - rad, oy - rad, ox + rad, oy + rad), fill=col)
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).ellipse((1, 1, n - 2, n - 2), fill=255)
    out = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    sheen = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sheen)
    sr = int(n * 0.28)
    sd.ellipse(
        (n // 2 - sr, int(n * 0.16) - int(sr * 0.55), n // 2 + sr, int(n * 0.16) + int(sr * 0.55)),
        fill=(255, 255, 255, 38),
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=max(2, n // 28)))
    out = Image.alpha_composite(out, sheen)
    return out.resize((size, size), Image.Resampling.LANCZOS)


def render_badge(kind: int) -> Image.Image:
    color = WARN if kind == 2 else DANGER
    punch = (
        max(0, int(color[0] * 0.78)),
        max(0, int(color[1] * 0.62)),
        max(0, int(color[2] * 0.42)),
        255,
    )
    label = "주의" if kind == 2 else "위험"
    img = Image.new("RGBA", (WIN_W, WIN_H), (0, 0, 0, 0))
    cy = WIN_H / 2
    r, g, b = color[0], color[1], color[2]

    glow = Image.new("RGBA", (WIN_W, WIN_H), (0, 0, 0, 0))
    outer = _soft_circle(MAIN_D + 24, (r, g, b, 70))
    inner = _soft_circle(MAIN_D + 10, (r, g, b, 110))
    glow.paste(outer, (PAD - 12, PAD - 12), outer)
    glow.paste(inner, (PAD - 5, PAD - 5), inner)
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(radius=8)))

    body = Image.new("RGBA", (WIN_W, WIN_H), (0, 0, 0, 0))
    main = _orb_body(MAIN_D, color)
    body.paste(main, (PAD, PAD), main)

    s = SCALE
    mark = Image.new("RGBA", (MAIN_D * s, MAIN_D * s), (0, 0, 0, 0))
    md = ImageDraw.Draw(mark)
    mcx, mcy = MAIN_D * s / 2, MAIN_D * s / 2
    k = MAIN_D / 58
    icon_cy = mcy - 8 * s * k
    hw, sz = 9.4 * s * k, 17.8 * s * k
    md.polygon(
        [(mcx, icon_cy - sz * 0.56), (mcx + hw, icon_cy + sz * 0.48), (mcx - hw, icon_cy + sz * 0.48)],
        fill=(255, 255, 255, 255),
    )
    bar_w, bar_h, dot_r = 1.9 * s * k, 6.6 * s * k, 1.35 * s * k
    md.rounded_rectangle(
        (mcx - bar_w / 2, icon_cy - 5.4 * s * k, mcx + bar_w / 2, icon_cy - 5.4 * s * k + bar_h),
        radius=max(1, int(1.2 * s * k)),
        fill=punch,
    )
    dy = icon_cy + 2.7 * s * k
    md.ellipse((mcx - dot_r, dy, mcx + dot_r, dy + dot_r * 2), fill=punch)
    font = _font(max(8, int(12 * s * k)))
    bbox = md.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    md.text(
        (mcx - tw / 2 - bbox[0], mcy + 8 * s * k - th / 2 - bbox[1]),
        label,
        font=font,
        fill=(255, 255, 255, 255),
    )
    mark = mark.resize((MAIN_D, MAIN_D), Image.Resampling.LANCZOS)
    body.paste(mark, (PAD, PAD), mark)
    img = Image.alpha_composite(img, body)

    x = PAD + MAIN_D + GAP
    for d, op in zip(DOT_D, (0.78, 0.42, 0.18)):
        dot = _soft_circle(d, (r, g, b, int(255 * op)))
        img.paste(dot, (int(x), int(cy - d / 2)), dot)
        x += d + GAP
    return img


def _toplevel_hwnd(hwnd: int) -> int:
    user32 = ctypes.windll.user32
    ga_root = 2
    try:
        root = user32.GetAncestor(hwnd, ga_root)
        return int(root) if root else hwnd
    except Exception:
        return hwnd


def _set_exstyle(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    if ctypes.sizeof(ctypes.c_void_p) == 8:
        get = user32.GetWindowLongPtrW
        setl = user32.SetWindowLongPtrW
    else:
        get = user32.GetWindowLongW
        setl = user32.SetWindowLongW
    style = get(hwnd, GWL_EXSTYLE)
    setl(
        hwnd,
        GWL_EXSTYLE,
        style | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST,
    )


def _paint_layered(hwnd: int, image: Image.Image, x: int, y: int) -> None:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    img = image.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    w, h = img.size
    data = img.tobytes("raw", "BGRA")
    hdc_screen = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = BI_RGB
    bits = ctypes.c_void_p()
    hbmp = gdi32.CreateDIBSection(hdc_mem, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
    if not hbmp or not bits:
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        return
    ctypes.memmove(bits, data, len(data))
    old = gdi32.SelectObject(hdc_mem, hbmp)
    blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)
    user32.UpdateLayeredWindow(
        hwnd,
        hdc_screen,
        ctypes.byref(POINT(int(x), int(y))),
        ctypes.byref(SIZE(w, h)),
        hdc_mem,
        ctypes.byref(POINT(0, 0)),
        0,
        ctypes.byref(blend),
        ULW_ALPHA,
    )
    gdi32.SelectObject(hdc_mem, old)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_screen)
    user32.SetWindowPos(
        hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOACTIVATE | SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW
    )


def _overlay_main(cmd_q: mp.Queue) -> None:
    import tkinter as tk

    user32 = ctypes.windll.user32
    root = tk.Tk()
    root.overrideredirect(True)
    root.geometry(f"{WIN_W}x{WIN_H}+0+0")
    root.update_idletasks()
    hwnd = _toplevel_hwnd(int(root.winfo_id()))
    _set_exstyle(hwnd)

    badge = {"img": None}
    anim = {"phase": "idle", "t0": 0.0}
    blank = Image.new("RGBA", (WIN_W, WIN_H), (0, 0, 0, 0))

    def geom():
        sw = user32.GetSystemMetrics(0)
        return sw - WIN_W, sw, TOP_Y

    def paint(x, y, img=None):
        _paint_layered(hwnd, img if img is not None else badge["img"] or blank, x, y)

    def tick():
        try:
            while True:
                cmd, payload = cmd_q.get_nowait()
                if cmd == "quit":
                    root.destroy()
                    return
                if cmd == "hide":
                    anim["phase"] = "out"
                    anim["t0"] = time.time()
                elif cmd == "show":
                    print(f"[바른자세] 알림 표시: {'주의' if payload == 2 else '위험'}", flush=True)
                    badge["img"] = render_badge(int(payload))
                    x_shown, x_hidden, y = geom()
                    root.deiconify()
                    paint(x_hidden, y)
                    anim["phase"] = "in"
                    anim["t0"] = time.time()
        except queue.Empty:
            pass
        except Exception as e:
            print(f"[바른자세] 알림 오류: {e}", flush=True)

        if badge["img"] is None:
            root.after(16, tick)
            return
        x_shown, x_hidden, y = geom()
        now = time.time()
        ph = anim["phase"]
        if ph == "in":
            t = _ease_out((now - anim["t0"]) / SLIDE_SEC)
            paint(x_hidden + (x_shown - x_hidden) * t, y)
            if now - anim["t0"] >= SLIDE_SEC:
                anim["phase"] = "hold"
                anim["t0"] = now
                paint(x_shown, y)
        elif ph == "hold":
            paint(x_shown, y)
            if now - anim["t0"] >= HOLD_SEC:
                anim["phase"] = "out"
                anim["t0"] = now
        elif ph == "out":
            t = _ease_out((now - anim["t0"]) / SLIDE_SEC)
            paint(x_shown + (x_hidden - x_shown) * t, y)
            if now - anim["t0"] >= SLIDE_SEC:
                anim["phase"] = "idle"
                paint(x_hidden, y, blank)
                root.withdraw()
        root.after(16, tick)

    _, x_hidden, y = geom()
    paint(x_hidden, y, blank)
    root.withdraw()
    root.after(16, tick)
    root.mainloop()


AUTHKEY = b"baruna-overlay-v1"
_OVERLAY_SCRIPT = Path(__file__).resolve().parent / "overlay_run.py"


class _ConnQueue:
    def __init__(self, conn):
        self._conn = conn
        self._lock = threading.Lock()

    def put(self, item) -> None:
        with self._lock:
            self._conn.send(item)

    def get_nowait(self):
        if self._conn.poll():
            return self._conn.recv()
        raise queue.Empty


def run_overlay_server(port: int) -> None:
    listener = Listener(("127.0.0.1", port), authkey=AUTHKEY)
    conn = listener.accept()
    _overlay_main(_ConnQueue(conn))


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


class DesktopOverlay:
    def __init__(self):
        self._q: _ConnQueue | None = None
        self._proc: subprocess.Popen | None = None
        self._last: int | None = None
        self._lock = threading.Lock()

    def _alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self):
        if sys.platform != "win32":
            return
        if self._alive() and self._q is not None:
            return
        self.shutdown()
        try:
            port = _free_port()
            flags = 0
            if sys.platform == "win32":
                flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self._proc = subprocess.Popen(
                [sys.executable, str(_OVERLAY_SCRIPT), str(port)],
                cwd=str(Path(__file__).resolve().parent.parent),
                creationflags=flags,
            )
            deadline = time.time() + 5.0
            last_err = None
            while time.time() < deadline:
                try:
                    conn = Client(("127.0.0.1", port), authkey=AUTHKEY)
                    self._q = _ConnQueue(conn)
                    print("[바른자세] 데스크톱 알림 프로세스 시작", flush=True)
                    return
                except (ConnectionRefusedError, OSError) as e:
                    last_err = e
                    time.sleep(0.05)
            raise RuntimeError(last_err)
        except Exception as e:
            print(f"[바른자세] 알림 프로세스 시작 실패: {e}", flush=True)
            self.shutdown()

    def notify(self, grade_label) -> None:
        self.start()
        g = _grade_key(grade_label)
        if g is None or self._q is None:
            return
        with self._lock:
            if g == 1:
                if self._last not in (None, 1):
                    try:
                        self._q.put(("hide", None))
                    except Exception:
                        pass
                self._last = 1
                return
            self._last = g
        try:
            self._q.put(("show", g))
        except Exception as e:
            print(f"[바른자세] 알림 전송 실패: {e}", flush=True)
            self._q = None
            self.start()
            if self._q is not None:
                self._q.put(("show", g))

    def reset(self) -> None:
        with self._lock:
            self._last = None
        if self._q is not None:
            try:
                self._q.put(("hide", None))
            except Exception:
                pass

    def shutdown(self) -> None:
        if self._q is not None:
            try:
                self._q.put(("quit", None))
            except Exception:
                pass
        self._q = None
        if self._proc is not None and self._proc.poll() is None:
            try:
                self._proc.wait(timeout=1.5)
            except Exception:
                pass
            if self._proc.poll() is None:
                self._proc.terminate()
        self._proc = None


overlay = DesktopOverlay()
