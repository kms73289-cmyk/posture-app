"""AlertsPage — alert history with posture snapshots, sorted by severity."""
import os
import threading
import tkinter as tk

try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

_IMG_SEMAPHORE = threading.Semaphore(3)   # 동시 이미지 로드 최대 3개

from config import (
    FONT, BG_APP, BG_CARD, BG_ACTIVE, ACCENT,
    TEXT_PRI, TEXT_SEC, TEXT_HINT,
    CLR_GOOD, CLR_WARN, CLR_DANGER, CLR_BLUE, CLR_BORDER,
    score_color,
)

THUMB_W = 190
THUMB_H = 143

# (레이블, 단위, m→표시단위 배율, 바 최대값, 가중치 표시)
_AXES = [
    ("축1 목굴곡", "°",  1.0,   30.0, "x2"),
    ("축2 앞돌출", "cm", 100.0, 15.0, ""),
    ("축3 측방",   "°",  1.0,   20.0, ""),
    ("축4 어깨",   "°",  1.0,   12.0, ""),
]
_RAW_KEYS = ["neck_flexion", "forward_dist", "lateral_tilt", "shoulder_tilt"]
_WEIGHTS  = [2, 1, 1, 1]
_BAR_W    = 120


class AlertsPage(tk.Frame):
    def __init__(self, parent, data_manager, **kwargs):
        super().__init__(parent, bg=BG_APP, **kwargs)
        self.data_manager = data_manager
        self._sort_mode   = "score"   # "score" | "time"
        self._img_refs    = []
        self._build_ui()
        self.refresh()

    # ── UI 구조 ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # 헤더
        hdr = tk.Frame(self, bg=BG_APP)
        hdr.pack(fill="x", padx=20, pady=(18, 0))

        left = tk.Frame(hdr, bg=BG_APP)
        left.pack(side="left")
        tk.Label(left, text="알림 기록", bg=BG_APP, fg=TEXT_PRI,
                 font=(FONT, 18, "bold")).pack(anchor="w")
        tk.Label(left, text="경고 발생 시점의 자세 스냅샷  —  기준 대비 편차 표시",
                 bg=BG_APP, fg=TEXT_SEC, font=(FONT, 10)).pack(anchor="w")

        # 정렬 버튼
        sort_f = tk.Frame(hdr, bg=BG_APP)
        sort_f.pack(side="right", anchor="n", pady=6)
        tk.Label(sort_f, text="정렬", bg=BG_APP, fg=TEXT_HINT,
                 font=(FONT, 8)).pack(side="left", padx=(0, 6))
        self._btn_score = self._mk_sort_btn(sort_f, "나쁜 자세 순", "score")
        self._btn_time  = self._mk_sort_btn(sort_f, "최근순",       "time")
        self._btn_score.pack(side="left", padx=(0, 4))
        self._btn_time.pack(side="left")
        self._refresh_sort_btns()

        tk.Frame(self, bg=CLR_BORDER, height=1).pack(fill="x", padx=20, pady=(10, 0))

        # 스크롤 영역
        self._canvas = tk.Canvas(self, bg=BG_APP, highlightthickness=0)
        vbar = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=vbar.set)
        vbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self._inner = tk.Frame(self._canvas, bg=BG_APP)
        self._win   = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.bind("<Configure>",
                         lambda e: self._canvas.configure(
                             scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>",
                          lambda e: self._canvas.itemconfig(self._win, width=e.width))
        self._canvas.bind("<Enter>",
                          lambda e: self._canvas.bind_all("<MouseWheel>", self._scroll))
        self._canvas.bind("<Leave>",
                          lambda e: self._canvas.unbind_all("<MouseWheel>"))

    def _scroll(self, e):
        self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _mk_sort_btn(self, parent, label, mode):
        btn = tk.Label(parent, text=label, bg=BG_CARD, fg=TEXT_SEC,
                       font=(FONT, 9), padx=10, pady=4, cursor="hand2",
                       highlightbackground=CLR_BORDER, highlightthickness=1)
        btn.bind("<Button-1>", lambda e: self._set_sort(mode))
        return btn

    def _set_sort(self, mode):
        self._sort_mode = mode
        self._refresh_sort_btns()
        self.refresh()

    def _refresh_sort_btns(self):
        for btn, mode in [(self._btn_score, "score"), (self._btn_time, "time")]:
            active = self._sort_mode == mode
            btn.config(
                bg=BG_ACTIVE if active else BG_CARD,
                fg=ACCENT    if active else TEXT_SEC,
                font=(FONT, 9, "bold") if active else (FONT, 9),
                highlightbackground=ACCENT if active else CLR_BORDER,
            )

    # ── 새로고침 ──────────────────────────────────────────────────────────────
    def refresh(self):
        for w in self._inner.winfo_children():
            w.destroy()
        self._img_refs.clear()

        alerts = self.data_manager.get_all_alerts()

        if not alerts:
            tk.Label(self._inner, text="아직 알림 기록이 없습니다.",
                     bg=BG_APP, fg=TEXT_HINT, font=(FONT, 12)).pack(pady=60)
            return

        if self._sort_mode == "score":
            alerts.sort(key=lambda a: a.get("score") or 0, reverse=True)
        else:
            alerts.sort(
                key=lambda a: (a.get("date", ""), a.get("time", "")),
                reverse=True,
            )

        # 최대 100개만 표시 (위젯 생성 비용 제한)
        alerts = alerts[:100]

        for alert in alerts:
            self._build_card(self._inner, alert)

        tk.Frame(self._inner, bg=BG_APP, height=20).pack()

    # ── 카드 ──────────────────────────────────────────────────────────────────
    def _build_card(self, parent, alert):
        score = alert.get("score")
        grade = alert.get("grade", "")
        col   = score_color(score) if score is not None else TEXT_HINT

        card = tk.Frame(parent, bg=BG_CARD,
                        highlightbackground=col, highlightthickness=1)
        card.pack(fill="x", padx=20, pady=(8, 0))

        # ── 카드 헤더 ─────────────────────────────────────────────────────────
        ch = tk.Frame(card, bg=col)
        ch.pack(fill="x")

        if grade:
            tk.Label(ch, text=f" {grade} ", bg=col, fg="#FFFFFF",
                     font=(FONT, 9, "bold"), padx=4, pady=3).pack(side="left")
        score_txt = f"PSI {score:.1f}점" if score is not None else "--"
        tk.Label(ch, text=score_txt, bg=col, fg="#FFFFFF",
                 font=(FONT, 9, "bold")).pack(side="left", padx=(6, 0))

        dt_txt = f"{alert.get('date', '')}  {alert.get('time', '')}"
        tk.Label(ch, text=dt_txt, bg=col, fg="#FFFFFF",
                 font=(FONT, 8)).pack(side="right", padx=10)

        # ── 카드 바디 ─────────────────────────────────────────────────────────
        body = tk.Frame(card, bg=BG_CARD)
        body.pack(fill="x", padx=10, pady=8)

        # 썸네일 (왼쪽)
        thumb_f = tk.Frame(body, bg="#111111", width=THUMB_W, height=THUMB_H)
        thumb_f.pack(side="left", padx=(0, 12))
        thumb_f.pack_propagate(False)

        thumb_lbl = tk.Label(thumb_f, bg="#111111", fg=TEXT_HINT,
                             font=(FONT, 8), text="사진 없음")
        thumb_lbl.pack(expand=True)

        img_path = alert.get("img_path")
        if img_path and os.path.exists(img_path) and _PIL_OK:
            self._load_image_async(img_path, thumb_lbl)

        # 오른쪽: 메시지 + 축별 편차
        right = tk.Frame(body, bg=BG_CARD)
        right.pack(side="left", fill="both", expand=True)

        msg = alert.get("message", "")
        if msg:
            tk.Label(right, text=msg, bg=BG_CARD, fg=TEXT_SEC,
                     font=(FONT, 9), anchor="w").pack(fill="x", pady=(0, 6))

        tk.Frame(right, bg=CLR_BORDER, height=1).pack(fill="x", pady=(0, 6))

        has_axes = any(alert.get(f"axis{i+1}") is not None for i in range(4))
        if has_axes:
            self._build_axes(right, alert)
        else:
            tk.Label(right, text="축별 데이터 없음 (구버전 기록)",
                     bg=BG_CARD, fg=TEXT_HINT, font=(FONT, 8)).pack(anchor="w")

    # ── 이미지 백그라운드 로딩 ────────────────────────────────────────────────
    def _load_image_async(self, img_path, label):
        """PIL 열기/리사이즈는 백그라운드 스레드, PhotoImage 생성은 메인 스레드."""
        def _worker():
            with _IMG_SEMAPHORE:
                try:
                    pil = Image.open(img_path)
                    pil.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
                except Exception:
                    return
            # 메인 스레드에서 PhotoImage 생성 및 적용
            label.after(0, lambda p=pil: self._apply_image(label, p))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_image(self, label, pil_img):
        if not label.winfo_exists():
            return
        try:
            photo = ImageTk.PhotoImage(pil_img)
            label.config(image=photo, text="")
            self._img_refs.append(photo)
        except Exception:
            pass

    # ── 축별 편차 바 ──────────────────────────────────────────────────────────
    def _build_axes(self, parent, alert):
        pts  = [alert.get(f"axis{i+1}") for i in range(4)]
        raws = [alert.get(k) for k in _RAW_KEYS]

        # 가장 기여도가 높은 축 (가중 점수 기준)
        weighted  = [(p or 0) * w for p, w in zip(pts, _WEIGHTS)]
        max_w_val = max(weighted)
        worst_idx = weighted.index(max_w_val) if max_w_val > 0 else -1

        for i, (lbl, unit, mult, bar_max, wlbl) in enumerate(_AXES):
            row = tk.Frame(parent, bg=BG_CARD)
            row.pack(fill="x", pady=1)

            # 레이블 (최대 기여 축은 강조)
            is_worst = (i == worst_idx)
            lbl_col  = CLR_DANGER if is_worst else TEXT_SEC
            marker   = ">" if is_worst else " "
            tk.Label(row, text=f"{marker} {lbl}", bg=BG_CARD, fg=lbl_col,
                     font=(FONT, 8, "bold") if is_worst else (FONT, 8),
                     width=11, anchor="w").pack(side="left")

            # Canvas 바
            bar = tk.Canvas(row, bg=CLR_BORDER, height=8, width=_BAR_W,
                            highlightthickness=0)
            bar.pack(side="left", padx=(4, 6))

            raw = raws[i]
            pt  = pts[i]
            if raw is not None:
                val  = abs(raw) * mult
                frac = min(1.0, val / bar_max)
                bw   = max(1, int(_BAR_W * frac))
                if pt is None:  bclr = CLR_BORDER
                elif pt <= 1:   bclr = CLR_BLUE
                elif pt == 2:   bclr = CLR_GOOD
                elif pt == 3:   bclr = CLR_WARN
                else:           bclr = CLR_DANGER
                bar.create_rectangle(0, 0, bw, 8, fill=bclr, outline="")
                val_str = f"{val:.1f}{unit}"
            else:
                val_str = "--"

            # 수치
            tk.Label(row, text=val_str, bg=BG_CARD, fg=TEXT_PRI,
                     font=(FONT, 8), width=7, anchor="e").pack(side="left")

            # 점수 배지
            if pt is not None:
                badge = f"[{pt}pt"
                if wlbl:
                    badge += f" {wlbl}"
                badge += "]"
                pt_col = (CLR_DANGER if pt >= 4 else
                          CLR_WARN   if pt == 3 else
                          TEXT_HINT)
                tk.Label(row, text=badge, bg=BG_CARD, fg=pt_col,
                         font=(FONT, 8)).pack(side="left", padx=(4, 0))
