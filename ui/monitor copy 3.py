"""MonitorPage — embedded posture measurement screen."""
import tkinter as tk
import threading
import time

import cv2
from PIL import Image, ImageTk

from config import (
    FONT, BG_APP, BG_CARD, ACCENT, ACCENT_DRK,
    TEXT_PRI, TEXT_SEC, TEXT_HINT,
    CLR_GOOD, CLR_WARN, CLR_DANGER, CLR_BORDER,
    CAM_DISPLAY_W, SCORE_INTERVAL,
    score_color,
)
from analyzer import PostureAnalyzer
from ui.widgets import ScoreRingCanvas


class MonitorPage(tk.Frame):
    def __init__(self, parent, data_manager,
                 on_open_camera=None, on_stop_camera=None, **kwargs):
        super().__init__(parent, bg=BG_APP, **kwargs)
        self.data_manager = data_manager

        self.running = False
        self.hidden = False
        self.analyzer = None
        self.cap = None
        self._frame_data = None
        self._frame_lock = threading.Lock()
        self._last_photo = None

        self._calibrated_once = False
        self._countdown = 0
        self._countdown_active = False

        self.last_save_time = 0
        self.session_start = time.time()
        self._session_sum = 0
        self._session_count = 0
        self._session_best = float("inf")

        self._build()
        self.after(100, self._refresh_ui)

    def _build(self):
        wrapper = tk.Frame(self, bg=BG_APP)
        wrapper.pack(fill="both", expand=True, padx=70, pady=32)

        self.main_card = tk.Frame(
            wrapper,
            bg=BG_CARD,
            highlightbackground=CLR_BORDER,
            highlightthickness=1
        )
        self.main_card.pack(fill="both", expand=True)

        self.title = tk.Label(
            self.main_card,
            text="오늘도 건강하게, 바른자세 측정을 시작할까요?",
            bg=BG_CARD,
            fg=TEXT_PRI,
            font=(FONT, 20, "bold")
        )
        self.title.pack(anchor="w", padx=40, pady=(35, 20))

        content = tk.Frame(self.main_card, bg=BG_CARD)
        content.pack(fill="both", expand=True, padx=40, pady=(0, 20))

        self.camera_box = tk.Frame(content, bg="#E8EEF5", height=300)
        self.camera_box.pack(side="left", fill="both", expand=True, padx=(0, 18))
        self.camera_box.pack_propagate(False)

        self.cam_lbl = tk.Label(
            self.camera_box,
            text="CAMERA",
            bg="#E8EEF5",
            fg="#64748B",
            font=(FONT, 26, "bold")
        )
        self.cam_lbl.pack(expand=True, fill="both")

        panel = tk.Frame(content, bg=BG_CARD, width=330)
        panel.pack(side="left", fill="y")
        panel.pack_propagate(False)

        self._status_title = tk.Label(
            panel,
            text="카메라 연결 대기 중",
            bg=BG_CARD,
            fg=TEXT_PRI,
            font=(FONT, 15, "bold")
        )
        self._status_title.pack(anchor="w", pady=(10, 4))

        self._status_desc = tk.Label(
            panel,
            text="측정 시작 버튼을 누르면 활성화됩니다.",
            bg=BG_CARD,
            fg=TEXT_SEC,
            font=(FONT, 9),
            wraplength=230,
            justify="left"
        )
        self._status_desc.pack(anchor="w", pady=(0, 18))

        score_card = tk.Frame(
            panel,
            bg=BG_CARD,
            highlightbackground=CLR_BORDER,
            highlightthickness=1
        )
        score_card.pack(fill="x", pady=(0, 10))

        tk.Label(
            score_card,
            text="현재 자세 점수",
            bg=BG_CARD,
            fg=TEXT_SEC,
            font=(FONT, 9)
        ).pack(anchor="w", padx=12, pady=(10, 2))

        self.ring = ScoreRingCanvas(score_card, size=110, ring_width=10, bg=BG_CARD)
        self.ring.pack(pady=(0, 4))
        self.ring.draw(None)

        self.score_lbl = tk.Label(
            score_card,
            text="--",
            bg=BG_CARD,
            fg=TEXT_HINT,
            font=(FONT, 15, "bold")
        )
        self.score_lbl.pack(pady=(0, 10))

        info_card = tk.Frame(
            panel,
            bg=BG_CARD,
            highlightbackground=CLR_BORDER,
            highlightthickness=1
        )
        info_card.pack(fill="x", pady=(0, 10))

        self.lbl_duration = self._row(info_card, "측정 시간", "00:00")
        self.lbl_avg = self._row(info_card, "평균 PSI", "--")
        self.lbl_best = self._row(info_card, "최고 PSI", "--")

        self._start_btn = tk.Button(
            panel,
            text="측정 시작하기",
            bg=ACCENT,
            fg="#FFFFFF",
            font=(FONT, 11, "bold"),
            bd=0,
            padx=24,
            pady=10,
            cursor="hand2",
            activebackground=ACCENT_DRK,
            activeforeground="#FFFFFF",
            command=self._on_start,
        )
        self._start_btn.pack(fill="x", pady=(6, 8))

        self._hide_btn = tk.Button(
            panel,
            text="화면 숨기기",
            bg=BG_CARD,
            fg=TEXT_SEC,
            font=(FONT, 10, "bold"),
            bd=0,
            padx=20,
            pady=9,
            cursor="hand2",
            command=self._hide_view,
        )

        self._recal_btn = tk.Button(
            panel,
            text="기준 재설정",
            bg=ACCENT,
            fg="#FFFFFF",
            font=(FONT, 10, "bold"),
            bd=0,
            padx=20,
            pady=9,
            cursor="hand2",
            command=self._recalibrate,
        )

        self._stop_btn = tk.Button(
            panel,
            text="측정 중지",
            bg="#FFF5F5",
            fg=CLR_DANGER,
            font=(FONT, 10, "bold"),
            bd=0,
            padx=20,
            pady=9,
            cursor="hand2",
            command=self._on_stop,
        )

    def _row(self, parent, label, value):
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", padx=12, pady=5)

        tk.Label(
            row,
            text=label,
            bg=BG_CARD,
            fg=TEXT_SEC,
            font=(FONT, 9),
            anchor="w"
        ).pack(side="left")

        value_lbl = tk.Label(
            row,
            text=value,
            bg=BG_CARD,
            fg=TEXT_PRI,
            font=(FONT, 9, "bold")
        )
        value_lbl.pack(side="right")
        return value_lbl

    def _on_start(self):
        if self.running:
            self._show_view()
            return

        self.running = True
        self.hidden = False
        self._calibrated_once = False
        self._countdown_active = False
        self._countdown = 0
        self.last_save_time = 0
        self.session_start = time.time()
        self._session_sum = 0
        self._session_count = 0
        self._session_best = float("inf")

        self._status_title.config(text="카메라 연결 중", fg=TEXT_PRI)
        self._status_desc.config(text="잠시만 기다려주세요.")
        self._start_btn.config(text="카메라 연결 중...", state="disabled")
      

        threading.Thread(target=self._camera_loop, daemon=True).start()

    def _camera_loop(self):
        self.analyzer = PostureAnalyzer()

        def alert_cb(msg, severity, snapshot=None):
            with self._frame_lock:
                data = self._frame_data
            frame_copy = data[0].copy() if data is not None else None
            try:
                self.data_manager.add_alert(
                    msg,
                    severity,
                    frame=frame_copy,
                    snapshot=snapshot
                )
            except TypeError:
                self.data_manager.add_alert(msg, severity)

        self.analyzer.set_alert_callback(alert_cb)
        self.analyzer.start_calibration()

        self.cap = cv2.VideoCapture(0)

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)
            frame, state = self.analyzer.process_frame(frame)

            with self._frame_lock:
                self._frame_data = (frame, state)

            time.sleep(0.08 if not self.hidden else 0.5)

        if self.cap:
            self.cap.release()

    def _refresh_ui(self):
        if not self.running:
            self.after(100, self._refresh_ui)
            return

        with self._frame_lock:
            data = self._frame_data

        if data is None:
            self._status_title.config(text="AI 모델 로딩 중", fg=TEXT_PRI)
            self._status_desc.config(text="카메라와 분석 모델을 준비하고 있습니다.")
            self.after(100, self._refresh_ui)
            return

        frame, state = data

        if not self.hidden:
            h, w = frame.shape[:2]
            disp_h = int(h * CAM_DISPLAY_W / w)
            resized = cv2.resize(frame, (CAM_DISPLAY_W, disp_h))
            img = Image.fromarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
            photo = ImageTk.PhotoImage(image=img)
            self._last_photo = photo
            self.cam_lbl.config(image=photo, text="", bg="#000000")

        if not state.get("calibrated"):
            rem = state.get("calib_remaining", 0)
            self._status_title.config(text="자세 기준 설정 중", fg=CLR_WARN)
            self._status_desc.config(text=f"바른 자세로 앉아주세요. {rem}초 남음")
            self.score_lbl.config(text="기준 설정 중", fg=CLR_WARN)
            self.ring.draw(None)

        elif state.get("calibrated") and not self._calibrated_once:
            self._calibrated_once = True
            self._start_countdown()

        elif self._countdown_active:
            self._status_title.config(text="측정 시작 준비", fg=ACCENT)
            self._status_desc.config(text="자세를 유지해주세요.")
            self.score_lbl.config(text=str(self._countdown), fg=ACCENT)
            self.ring.draw(None)

        elif state.get("detected") and state.get("score") is not None:
            score = state["score"]
            grade = state["grade"]
            col = score_color(score)

            self._status_title.config(text="실시간 측정 중", fg=CLR_GOOD)
            self._status_desc.config(text="현재 자세를 분석하고 있습니다.")
            self.score_lbl.config(text=f"PSI {score:.1f}점 - {grade}", fg=col)
            self.ring.draw(score)

            elapsed = int(time.time() - self.session_start)
            m, s = divmod(elapsed, 60)
            self.lbl_duration.config(text=f"{m:02d}:{s:02d}")

            self._session_sum += score
            self._session_count += 1
            if score < self._session_best:
                self._session_best = score

            avg = self._session_sum / self._session_count
            self.lbl_avg.config(text=f"{avg:.1f}점", fg=score_color(avg))
            self.lbl_best.config(text=f"{self._session_best:.1f}점",
                                 fg=score_color(self._session_best))

            now = time.time()
            if now - self.last_save_time >= SCORE_INTERVAL:
                self.data_manager.add_score(score, grade)
                self.last_save_time = now

        else:
            self._status_title.config(text="사람을 감지할 수 없습니다", fg=TEXT_HINT)
            self._status_desc.config(text="카메라 앞에 앉아주세요.")

        self.after(100, self._refresh_ui)

    def _start_countdown(self):
        self._countdown = 3
        self._countdown_active = True
        self._countdown_tick()
        self._hide_btn.pack(fill="x", pady=(0, 8))
        self._recal_btn.pack(side="left", padx=6)
        self._stop_btn.pack(side="left", padx=6)

    def _countdown_tick(self):
        if not self.running:
            return

        if self._countdown > 0:
            self._status_title.config(text="측정 시작 준비", fg=ACCENT)
            self._status_desc.config(text="바른 자세를 유지해주세요.")
            self.score_lbl.config(text=str(self._countdown), fg=ACCENT)
            self._countdown -= 1
            self.after(1000, self._countdown_tick)
        else:
            self._countdown_active = False
            self._status_title.config(text="실시간 측정 중", fg=CLR_GOOD)
            self._status_desc.config(text="자세 분석이 시작되었습니다.")
            self._start_btn.config(text="모니터 보기", state="normal", bg="#2D7A5E")
            self._hide_btn.pack(fill="x", pady=(0, 8))
            self._recal_btn.pack(fill="x", pady=(0, 8))
            self._stop_btn.pack(fill="x")

    def _hide_view(self):
        if not self.running:
            return

        self.hidden = True
        self.cam_lbl.config(image="", text="화면이 숨겨졌습니다", bg="#E8EEF5", fg="#64748B")
        self._status_title.config(text="백그라운드 측정 중", fg=CLR_GOOD)
        self._status_desc.config(text="카메라 화면은 숨겨졌지만 자세 측정은 계속됩니다.")
        self._start_btn.config(text="모니터 보기", state="normal", bg="#2D7A5E")

    def _show_view(self):
        if not self.running:
            return

        self.hidden = False
        self._status_title.config(text="실시간 측정 중", fg=CLR_GOOD)
        self._status_desc.config(text="카메라 화면을 다시 표시했습니다.")
        self._start_btn.config(text="모니터 보기", state="normal", bg="#2D7A5E")

    def _on_stop(self):
        self.running = False
        self.hidden = False
        self._frame_data = None
        self._last_photo = None

        self.cam_lbl.config(image="", text="CAMERA", bg="#E8EEF5", fg="#64748B")
        self._status_title.config(text="카메라 연결 대기 중", fg=TEXT_PRI)
        self._status_desc.config(text="측정 시작 버튼을 누르면 활성화됩니다.")
        self.score_lbl.config(text="--", fg=TEXT_HINT)
        self.ring.draw(None)

        self.lbl_duration.config(text="00:00")
        self.lbl_avg.config(text="--", fg=TEXT_PRI)
        self.lbl_best.config(text="--", fg=TEXT_PRI)

        self._start_btn.config(text="측정 시작하기", state="normal", bg=ACCENT)
        self._hide_btn.pack_forget()
        self._recal_btn.pack_forget()
        self._stop_btn.pack_forget()
    
    def _recalibrate(self):
        if self.analyzer is None:
            return

        self.analyzer.start_calibration()

        self._calibrated_once = False
        self._countdown_active = False
        self._countdown = 0

        self.session_start = time.time()
        self._session_sum = 0
        self._session_count = 0
        self._session_best = float("inf")

        self._status_title.config(
            text="자세 기준 설정 중",
            fg=CLR_WARN
        )

        self._status_desc.config(
            text="바른 자세로 다시 앉아주세요."
        )
    def set_active(self, active: bool, calibrating: bool = False):
        pass