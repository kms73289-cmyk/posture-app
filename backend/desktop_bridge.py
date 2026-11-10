"""데스크톱 셸(창 숨김/복원/종료) 콜백. 웹 UI에서 API로 호출."""
from __future__ import annotations

from typing import Callable, Optional

minimize_cb: Optional[Callable[[], None]] = None
restore_cb: Optional[Callable[[], None]] = None
quit_cb: Optional[Callable[[], None]] = None


def minimize() -> dict:
    if minimize_cb is None:
        return {"ok": False, "desktop": False}
    minimize_cb()
    return {"ok": True, "desktop": True}


def restore() -> dict:
    if restore_cb is None:
        return {"ok": False, "desktop": False}
    restore_cb()
    return {"ok": True, "desktop": True}


def quit_app() -> dict:
    if quit_cb is None:
        return {"ok": False, "desktop": False}
    quit_cb()
    return {"ok": True, "desktop": True}
