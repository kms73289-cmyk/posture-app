"""MonitorPage — embedded camera posture monitoring."""
import time
from analyzer import PostureAnalyzer
from config import SCORE_INTERVAL
import tkinter as tk
import cv2
from PIL import Image, ImageTk

from config import (
    FONT, BG_APP, ACCENT, TEXT_PRI, TEXT_SEC,
    CLR_DANGER, CLR_BORDER
)


class MonitorPage(tk.Frame):
    def __init__(self, parent, data_manager, on_open_camera=None, on_stop_camera=None, **kwargs):
        super().__init__(parent, bg=BG_APP, **kwargs)
        self.data_manager = data_manager
        self.cap = None
        self.running = False
        self.hidden = False
        self.countdown = 3
        self._img_ref = None
        self._build()
        self.analyzer = PostureAnalyzer()
        self.last_score_time = 0
        self.analyzer.set_alert_callback(self._handle_alert)

    def _build(self):
        container = tk.Frame(self, bg=BG_APP)
        container.pack(fill="both", expand=True, padx=60, pady=45)

        tk.Label(
            container,
            text="오늘도 건강하게, 바른 자세 측정을 시작할까요?",
            bg=BG_APP,
            fg=TEXT_PRI,
            font=(FONT, 24, "bold")
        ).pack(anchor="w", pady=(10, 30))

        inner = tk.Frame(container, bg=BG_APP)
        inner.pack(anchor="n")

        self.camera_card = tk.Frame(inner, bg="#E2E8F0", width=800, height=450)
        self.camera_card.pack()
        self.camera_card.pack_propagate(False)

        self.msg_lbl = tk.Label(
            self.camera_card,
            text="카메라 연결 대기 중\n\n측정 시작 버튼을 눌러주세요.",
            bg="#E2E8F0",
            fg="#475569",
            font=(FONT, 16, "bold"),
            justify="center"
        )
        self.msg_lbl.pack(expand=True)

        self.video_lbl = tk.Label(self.camera_card, bg="#000000")
        self.video_lbl.place_forget()

        self.btn_start = tk.Button(
            inner,
            text="측정 시작하기",
            bg=ACCENT,
            fg="#FFFFFF",
            bd=0,
            font=(FONT, 12, "bold"),
            command=self.start_measure
        )
        self.btn_start.pack(fill="x", ipady=10, pady=(18, 0))

        self.btn_bar = tk.Frame(inner, bg=BG_APP)

        tk.Button(
            self.btn_bar,
            text="종료하기",
            bg="#EF4444",
            fg="#FFFFFF",
            bd=0,
            font=(FONT, 11, "bold"),
            command=self.stop_measure
        ).pack(side="left", fill="x", expand=True, ipady=10)

        tk.Button(
            self.btn_bar,
            text="기준 재측정",
            bg=ACCENT,
            fg="#FFFFFF",
            bd=0,
            font=(FONT, 11, "bold"),
            command=self.reset_calibration
        ).pack(side="left", fill="x", expand=True, ipady=10, padx=10)

        self.btn_hide = tk.Button(
            self.btn_bar,
            text="화면 숨기기",
            bg="#E2E8F0",
            fg=TEXT_PRI,
            bd=0,
            font=(FONT, 11, "bold"),
            command=self.hide_screen
        )
        self.btn_hide.pack(side="left", fill="x", expand=True, ipady=10)

    def start_measure(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.msg_lbl.config(text="카메라를 연결할 수 없습니다.")
            return

        self.running = True
        self.hidden = False
        self.analyzer.start_calibration()

        self.btn_start.pack_forget()
        self.btn_bar.pack(fill="x", pady=(18, 0))

        self.video_lbl.place(x=0, y=0, relwidth=1, relheight=1)
        self.msg_lbl.place(x=0, y=0, relwidth=1, height=70)
        self.msg_lbl.config(
            text="바른 자세의 기준을 잡는 중입니다. 움직이지 마세요!",
            bg="#1C1C1C",
            fg="#FFFFFF",
            font=(FONT, 13, "bold")
        )

        self.countdown = 3
        self._update_camera()
        self._tick_countdown()

    def _tick_countdown(self):
        if not self.running:
            return

        if self.countdown <= 0:
            self.msg_lbl.config(text="측정 중입니다.")
            return

        self.msg_lbl.config(text=f"바른 자세의 기준을 잡는 중입니다. 움직이지 마세요!\n{self.countdown}")
        self.countdown -= 1
        self.after(1000, self._tick_countdown)

    def _update_camera(self):
        if not self.running or self.cap is None:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.after(30, self._update_camera)
            return

        self.last_frame = frame.copy()

        processed, state = self.analyzer.process_frame(frame)

        score = state.get("score")
        grade = state.get("grade")

        if score is not None:
            now = time.time()
            if now - self.last_score_time >= SCORE_INTERVAL:
                self.data_manager.add_score(score, grade)
                self.last_score_time = now

        if not self.hidden:
            show = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            show = cv2.resize(show, (800, 450))
            img = Image.fromarray(show)
            photo = ImageTk.PhotoImage(img)
            self._img_ref = photo
            self.video_lbl.config(image=photo)

        self.after(30, self._update_camera)
        
    def show_screen(self):
        self.hidden = False
        self.video_lbl.place(x=0, y=0, relwidth=1, relheight=1)
        self.msg_lbl.place(x=0, y=0, relwidth=1, height=70)
        self.msg_lbl.config(
            text="측정 중입니다.",
            bg="#1C1C1C",
            fg="#FFFFFF",
            font=(FONT, 13, "bold")
        )
        self.btn_hide.config(text="화면 숨기기", command=self.hide_screen)
    
    def _handle_alert(self, message, severity, snapshot=None):
        self.data_manager.add_alert(
        message,
        severity,
        frame=getattr(self, "last_frame", None),
        snapshot=snapshot
    )

    def stop_measure(self):
        self.running = False
        self.hidden = False

        if self.cap:
            self.cap.release()
            self.cap = None

        self.video_lbl.config(image="")
        self.video_lbl.place_forget()
        self.msg_lbl.place_forget()
        self.msg_lbl.pack(expand=True)
        self.msg_lbl.config(
            text="카메라 연결 대기 중\n\n측정 시작 버튼을 눌러주세요.",
            bg="#E2E8F0",
            fg="#475569",
            font=(FONT, 16, "bold")
        )

        self.btn_bar.pack_forget()
        self.btn_start.pack(fill="x", ipady=10, pady=(18, 0))

    def set_active(self, active: bool, calibrating: bool = False):
        pass