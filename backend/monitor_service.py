"""카메라 스레드 + 세션 통계 + 배너. ui/camera_window.py · warning_banner.py 이식."""
from __future__ import annotations

import math
import sys
import threading
import time
from typing import Optional

import cv2
import numpy as np

from config import SCORE_INTERVAL, score_grade
from analyzer import PostureAnalyzer
from backend import app_log
from backend.desktop_overlay import overlay as desktop_overlay

# ui/warning_banner.py
GOOD_HOLD_SEC = 3

_WORST_AXIS_KO = {
    "neck": "목 굴곡",
    "forward": "머리 앞돌출",
    "lateral": "측방 기울기",
    "shoulder": "어깨 기울기",
}


class BannerLogic:
    """PostureWarningBanner 상태머신 (tk 창 없이 필드만)."""

    def __init__(self):
        self.show = False
        self.grade: Optional[int] = None  # 1|2|3
        self.message = ""
        self.sub = ""
        self._good_since: Optional[float] = None

    def hide_immediately(self):
        self.show = False
        self.grade = None
        self.message = ""
        self.sub = ""
        self._good_since = None

    def update(self, grade_label, detected, calibrated, cause=None):
        if not calibrated or not detected or grade_label is None:
            return
        is_bad = grade_label in ("주의", "부적정")
        if is_bad:
            self._good_since = None
            if grade_label == "부적정":
                if cause == "neck":
                    msg = "거북목이 감지되었습니다! 즉시 자세를 교정해주세요."
                else:
                    msg = "자세가 부적정합니다. 즉시 교정해주세요."
                g = 3
            else:
                msg = "자세가 나빠지고 있습니다. 바르게 앉아주세요."
                g = 2
            self.show = True
            self.grade = g
            self.message = msg
            self.sub = "자세를 바르게 교정해주세요."
        else:
            if self.show:
                if self._good_since is None:
                    self._good_since = time.time()
                remaining = GOOD_HOLD_SEC - (time.time() - self._good_since)
                if remaining <= 0:
                    self.hide_immediately()
                else:
                    secs = math.ceil(remaining)
                    self.sub = f"자세 개선 중...  {secs}초 후 사라집니다."

    def to_dict(self):
        return {
            "show": self.show,
            "grade": self.grade,
            "message": self.message,
            "sub": self.sub,
        }


class MonitorService:
    def __init__(self, data_manager, app_settings):
        self.data_manager = data_manager
        self.app_settings = app_settings
        self.analyzer: Optional[PostureAnalyzer] = None
        self._model_loading = False
        self._preload_lock = threading.Lock()

        self._running = False
        self._camera_ok = False
        self._arm_first_calib = False
        self._visible = True
        self._stop_event = threading.Event()
        self._cam_thread: Optional[threading.Thread] = None
        self._tick_thread: Optional[threading.Thread] = None

        self._frame_lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._state: dict = {}
        self._jpeg: Optional[bytes] = None

        self.last_save_time = 0.0
        self.session_start = time.time()
        self._session_sum = 0.0
        self._session_count = 0
        self._session_best = float("inf")
        self._calibration_done = False
        self._banner_active = False
        self._banner_cooldown_start: Optional[float] = None
        self._overlay_last_at = 0.0
        self._banner = BannerLogic()
        self._ws_clients: list = []
        self._ws_lock = threading.Lock()

    # ── 프리로드 ──────────────────────────────────────────────────────────────
    def preload_analyzer(self):
        with self._preload_lock:
            if self.analyzer is not None:
                return
            self._model_loading = True
            try:
                app_log.info("analyzer", "preload_begin")
                self.analyzer = PostureAnalyzer()
                app_log.info("analyzer", "preload_ok")
            except Exception as e:
                app_log.exception("analyzer", "preload_fail", e)
            finally:
                self._model_loading = False

    def ensure_analyzer(self) -> PostureAnalyzer:
        if self.analyzer is None:
            self.preload_analyzer()
        if self.analyzer is None:
            raise RuntimeError("자세 분석 모델을 불러오지 못했습니다.")
        return self.analyzer

    def _bind_alert_callback(self):
        def _alert_cb(msg, severity, snapshot=None):
            with self._frame_lock:
                frame = None if self._frame is None else self._frame.copy()
            try:
                self.data_manager.add_alert(msg, severity, frame=frame, snapshot=snapshot)
            except Exception:
                pass

        self.analyzer.set_alert_callback(_alert_cb)

    # ── 제어 ──────────────────────────────────────────────────────────────────
    def start(self) -> dict:
        app_log.info("measure", "start_called", running=self._running)
        if self._running:
            app_log.info("measure", "start_already_running")
            return {"ok": True, "already": True}
        try:
            self.ensure_analyzer()
        except Exception as e:
            app_log.exception("measure", "ensure_analyzer_fail", e)
            return {"ok": False, "error": f"자세 분석 모델을 불러오지 못했습니다: {e}"}
        app_log.info("measure", "analyzer_ready")
        self._bind_alert_callback()
        # 타이머는 첫 JPEG가 나온 뒤에 맞춤. 여기선 이전 세션 보정 상태만 리셋.
        self.analyzer.start_calibration()
        self._reset_session_stats(keep_banner=False)
        self._arm_first_calib = True
        self._stop_event.clear()
        self._running = True
        self._camera_ok = False
        self._cam_thread = threading.Thread(target=self._camera_loop, daemon=True)
        self._tick_thread = threading.Thread(target=self._tick_loop, daemon=True)
        self._cam_thread.start()
        self._tick_thread.start()
        try:
            desktop_overlay.start()
        except Exception as e:
            app_log.exception("overlay", "start_fail", e)
        app_log.info("measure", "start_ok")
        return {"ok": True, "already": False}

    def stop(self) -> dict:
        if not self._running:
            return {"ok": True, "already": True}
        self._running = False
        self._stop_event.set()
        self._camera_ok = False
        self._arm_first_calib = False
        self._banner.hide_immediately()
        desktop_overlay.reset()
        with self._frame_lock:
            self._frame = None
            self._jpeg = None
            self._state = {}
        return {"ok": True, "already": False}

    def recalibrate(self) -> dict:
        """camera_window._recalibrate 와 동일."""
        if not self._running or self.analyzer is None:
            return {"ok": False, "error": "측정 중이 아닙니다."}
        self.analyzer.start_calibration()
        self._reset_session_stats(keep_banner=False)
        return {"ok": True}

    def _reset_session_stats(self, keep_banner: bool):
        self._session_sum = 0.0
        self._session_count = 0
        self._session_best = float("inf")
        self.session_start = time.time()
        self.last_save_time = 0.0
        self._calibration_done = False
        self._banner_active = False
        self._banner_cooldown_start = None
        self._overlay_last_at = 0.0
        if not keep_banner:
            self._banner.hide_immediately()

    def set_visible(self, visible: bool):
        self._visible = bool(visible)

    def shutdown(self):
        self.stop()
        desktop_overlay.shutdown()
        t = self._cam_thread
        if t and t.is_alive():
            t.join(timeout=2.0)

    # ── 카메라 ────────────────────────────────────────────────────────────────
    def _open_capture(self):
        """설치본·pythonw 환경에서는 MSMF보다 DirectShow가 안정적이다."""
        if sys.platform == "win32" and hasattr(cv2, "CAP_DSHOW"):
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if cap is not None and cap.isOpened():
                return cap
            if cap is not None:
                cap.release()
        return cv2.VideoCapture(0)

    def _camera_loop(self):
        cap = None
        miss = 0
        open_fail_logged = False
        try:
            app_log.info("camera", "loop_begin")
            while self._running and not self._stop_event.is_set():
                if cap is None or not cap.isOpened():
                    self._camera_ok = False
                    cap = self._open_capture()
                    if cap is None or not cap.isOpened():
                        if cap is not None:
                            cap.release()
                        cap = None
                        if not open_fail_logged:
                            app_log.error("camera", "open_fail", backend="CAP_DSHOW_then_default")
                            open_fail_logged = True
                        time.sleep(0.5)
                        continue
                    app_log.info("camera", "open_ok")
                    open_fail_logged = False
                    miss = 0
                if self.analyzer is None:
                    time.sleep(0.1)
                    continue
                try:
                    self.analyzer.alert_interval = self.app_settings.alert_interval
                except Exception:
                    pass
                ret, frame = cap.read()
                if not ret:
                    miss += 1
                    if miss > 20:
                        self._camera_ok = False
                        try:
                            cap.release()
                        except Exception:
                            pass
                        cap = None
                    time.sleep(0.05)
                    continue
                miss = 0
                frame = cv2.flip(frame, 1)
                if self._arm_first_calib:
                    self.analyzer.start_calibration()
                    self._reset_session_stats(keep_banner=False)
                    self._arm_first_calib = False
                try:
                    drawn, state = self.analyzer.process_frame(frame)
                except Exception as e:
                    if not getattr(self, "_mp_frame_fail_logged", False):
                        app_log.exception("mediapipe", "process_frame_fail", e)
                        self._mp_frame_fail_logged = True
                    time.sleep(0.05)
                    continue
                ok, buf = cv2.imencode(".jpg", drawn, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                jpeg = buf.tobytes() if ok else None
                with self._frame_lock:
                    self._frame = drawn
                    self._state = state
                    if jpeg is not None:
                        self._jpeg = jpeg
                if jpeg is not None:
                    self._camera_ok = True
                time.sleep(0.08)
        finally:
            if cap is not None:
                cap.release()
            self._camera_ok = False

    def _tick_loop(self):
        """원본 _refresh_ui: 100ms. 점수 저장·세션·배너."""
        while self._running and not self._stop_event.is_set():
            try:
                self._apply_tick()
            except Exception:
                pass
            time.sleep(0.1)

    def _apply_tick(self):
        if self.analyzer and self.app_settings:
            self.analyzer.alert_interval = self.app_settings.alert_interval

        with self._frame_lock:
            state = dict(self._state) if self._state else None

        if state is None:
            return

        if state.get("calibrated") and not self._calibration_done:
            self._calibration_done = True
            # 원본은 2초 후 withdraw. 새 UI에서는 화면 유지.

        if state.get("detected") and state.get("score") is not None and state.get("calibrated"):
            score = state["score"]
            grade = state["grade"]
            self._session_sum += score
            self._session_count += 1
            if score < self._session_best:
                self._session_best = score
            now = time.time()
            if now - self.last_save_time >= SCORE_INTERVAL:
                self.data_manager.add_score(
                    score, grade,
                    neck_load_kg=state.get("neck_load_kg"),
                    worst_axis=state.get("worst_axis"),
                )
                self.last_save_time = now

        grade = state.get("grade")
        if grade in ("주의", "부적정"):
            now = time.time()
            if not self._banner_active:
                interval = self.app_settings.alert_interval if self.app_settings else 30
                cooldown_elapsed = (
                    self._banner_cooldown_start is None
                    or now - self._banner_cooldown_start >= interval
                )
                if cooldown_elapsed:
                    self._banner_active = True
            effective_grade = grade if self._banner_active else "적정"
        else:
            if self._banner_active:
                self._banner_active = False
                self._banner_cooldown_start = time.time()
            effective_grade = grade
        self._banner.update(
            grade_label=effective_grade,
            detected=bool(state.get("detected")),
            calibrated=bool(state.get("calibrated")),
            cause=state.get("worst_axis"),
        )
        if state.get("calibrated"):
            overlay_grade = state.get("grade")
            now_ov = time.time()
            interval = self.app_settings.alert_interval if self.app_settings else 30
            if overlay_grade in ("주의", "부적정"):
                if now_ov - self._overlay_last_at >= interval:
                    desktop_overlay.notify(overlay_grade)
                    self._overlay_last_at = now_ov
            elif overlay_grade == "적정":
                desktop_overlay.notify("적정")

    # ── 조회 ──────────────────────────────────────────────────────────────────
    def latest_jpeg(self) -> Optional[bytes]:
        with self._frame_lock:
            return self._jpeg

    def get_state(self) -> dict:
        with self._frame_lock:
            st = dict(self._state) if self._state else {}

        def _num(v):
            if v is None:
                return None
            try:
                f = float(v)
            except (TypeError, ValueError):
                return None
            if f != f or f in (float("inf"), float("-inf")):
                return None
            return f

        axes = {
            "neck": {
                "value": _num(st.get("neck_flexion")),
                "unit": "°",
                "grade": st.get("axis1"),
            },
            "forward": {
                "value": _num(st.get("forward_dist")),
                "unit": "cm",
                "grade": st.get("axis2"),
            },
            "lateral": {
                "value": _num(st.get("lateral_tilt")),
                "unit": "°",
                "grade": st.get("axis3"),
            },
            "shoulder": {
                "value": _num(st.get("shoulder_tilt")),
                "unit": "°",
                "grade": st.get("axis4"),
            },
        }
        elapsed = int(time.time() - self.session_start) if self._running else 0
        avg = (self._session_sum / self._session_count) if self._session_count else None
        best = int(self._session_best) if self._session_count else None
        worst = st.get("worst_axis")
        if worst not in ("neck", "forward", "lateral", "shoulder"):
            worst = None
        calibrated = bool(st.get("calibrated"))
        calib_remaining = int(st.get("calib_remaining") or 0)
        if self._running and self.analyzer is not None:
            if self._arm_first_calib:
                calibrated = False
                calib_remaining = 0
            else:
                calibrated = bool(self.analyzer.calibrated)
                if not calibrated:
                    calib_remaining = max(
                        0,
                        int(self.analyzer.calib_time - (time.time() - self.analyzer.calib_start)),
                    )
        return {
            "running": self._running,
            "modelLoading": bool(self._model_loading),
            "cameraOk": self._camera_ok,
            "detected": bool(st.get("detected")),
            "calibrated": calibrated,
            "calibRemaining": calib_remaining,
            "grade": st.get("score"),
            "gradeLabel": st.get("grade"),
            "worstAxis": worst,
            "axes": axes,
            "neckLoadKg": _num(st.get("neck_load_kg")),
            "session": {
                "elapsedSec": elapsed,
                "avgGrade": avg,
                "bestGrade": best,
            },
            "banner": self._banner.to_dict(),
        }


monitor_service: Optional[MonitorService] = None
