"""REST / WebSocket / MJPEG 라우트."""
from __future__ import annotations

import os
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse

from config import DATA_FILE
from backend.models import (
    AlertOut, DaySummaryOut, HourlyPoint, InfoOut, MonthDayOut,
    ReportOut, SeriesPoint, SettingsIn, SettingsOut, TodayOut, GradeExpo,
)
from backend import report_service as rs
from backend import desktop_bridge

WEEKDAYS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
ALERT_INTERVALS = {10, 60, 600, 1800, 3600}


def build_router(monitor, data_manager, app_settings) -> APIRouter:
    router = APIRouter()

    @router.post("/api/measure/start")
    def measure_start():
        return monitor.start()

    @router.post("/api/measure/stop")
    def measure_stop():
        return monitor.stop()

    @router.post("/api/measure/recalibrate")
    def measure_recalibrate():
        result = monitor.recalibrate()
        if not result.get("ok"):
            raise HTTPException(400, result.get("error") or "재설정 실패")
        return result

    @router.post("/api/desktop/minimize")
    def desktop_minimize():
        return desktop_bridge.minimize()

    @router.post("/api/desktop/restore")
    def desktop_restore():
        return desktop_bridge.restore()

    @router.post("/api/desktop/shutdown")
    def desktop_shutdown():
        monitor.shutdown()
        return {"ok": True}

    @router.get("/api/video")
    async def video():
        import asyncio
        boundary = "frame"

        async def gen():
            try:
                while True:
                    jpeg = monitor.latest_jpeg()
                    if jpeg:
                        yield (
                            b"--" + boundary.encode() + b"\r\n"
                            b"Content-Type: image/jpeg\r\n"
                            b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                            + jpeg + b"\r\n"
                        )
                    await asyncio.sleep(0.08)
            except asyncio.CancelledError:
                return

        return StreamingResponse(
            gen(),
            media_type=f"multipart/x-mixed-replace; boundary={boundary}",
        )

    @router.websocket("/ws/state")
    async def ws_state(ws: WebSocket):
        await ws.accept()
        import asyncio
        try:
            async def recv_loop():
                while True:
                    data = await ws.receive_json()
                    if isinstance(data, dict) and "visible" in data:
                        monitor.set_visible(bool(data["visible"]))

            async def send_loop():
                while True:
                    await ws.send_json(monitor.get_state())
                    await asyncio.sleep(0.1)

            send = asyncio.create_task(send_loop())
            recv = asyncio.create_task(recv_loop())
            done, pending = await asyncio.wait(
                {send, recv}, return_when=asyncio.FIRST_COMPLETED
            )
            for t in pending:
                t.cancel()
            for t in done:
                exc = t.exception() if not t.cancelled() else None
                if exc and not isinstance(exc, WebSocketDisconnect):
                    raise exc
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    @router.get("/api/today", response_model=TodayOut)
    def today():
        d = date.today()
        d_str = d.isoformat()
        summary = data_manager.get_day_summary(d_str)
        hourly_raw = data_manager.get_hourly_scores(d_str)
        hourly = [
            HourlyPoint(hour=h, avg=hourly_raw.get(h))
            for h in rs.DASHBOARD_HOURS
        ]
        sitting = summary["total_duration"] if summary else 0
        good = summary["good_posture_sec"] if summary else 0
        sc_cnt = summary["score_count"] if summary else 0
        bad_cnt = summary["bad_count"] if summary else 0
        ratio = int(min(1.0, good / sitting) * 100) if sitting > 0 else None
        bad_pct = (bad_cnt / sc_cnt * 100) if sc_cnt > 0 else None
        return TodayOut(
            date=d_str,
            weekday=WEEKDAYS[d.weekday()],
            sittingSec=sitting,
            avgScore=summary["avg_score"] if summary else None,
            goodPostureSec=good,
            alertCount=summary["alert_count"] if summary else 0,
            scoreCount=sc_cnt,
            badCount=bad_cnt,
            totalDuration=sitting,
            goodRatioPct=ratio,
            badPct=bad_pct,
            hourly=hourly,
        )

    @router.get("/api/hourly")
    def hourly(date_str: str = Query(..., alias="date")):
        raw = data_manager.get_hourly_scores(date_str)
        return {"date": date_str, "hourly": {str(k): v for k, v in raw.items()}}

    @router.get("/api/month")
    def month(year: int, month: int):
        raw = data_manager.get_month_data(year, month)
        days = []
        for day, s in raw.items():
            days.append(MonthDayOut(
                day=day,
                date=date(year, month, day).isoformat(),
                avgScore=s["avg_score"],
                totalDuration=s["total_duration"],
                goodPostureSec=s["good_posture_sec"],
                alertCount=s["alert_count"],
                scoreCount=s["score_count"],
            ))
        return {"year": year, "month": month, "days": days}

    @router.get("/api/day", response_model=DaySummaryOut)
    def day(date_str: str = Query(..., alias="date")):
        summary = data_manager.get_day_summary(date_str)
        if not summary:
            return DaySummaryOut(date=date_str, hasData=False)
        total = summary["total_duration"]
        good = summary["good_posture_sec"]
        ratio = int((good / total) * 100) if total > 0 else 0
        return DaySummaryOut(
            date=date_str,
            hasData=True,
            avgScore=summary["avg_score"],
            goodRatioPct=ratio,
            alertCount=summary["alert_count"],
            totalDuration=total,
            goodPostureSec=good,
        )

    def _alerts_with_ids_for_date(date_str: str) -> list[dict]:
        with data_manager._lock:
            stored = list(data_manager.data.get(date_str, {}).get("alerts", []))
        out = []
        for idx, a in enumerate(stored):
            out.append(rs.alert_to_dict(a, date_str, idx))
        return out

    @router.get("/api/alerts")
    def alerts(
        date_str: Optional[str] = Query(None, alias="date"),
        sort: str = Query("time"),
        limit: int = Query(100, ge=1, le=500),
    ):
        if date_str in (None, "", "today"):
            if date_str == "today":
                items = _alerts_with_ids_for_date(date.today().isoformat())
            else:
                items = []
                with data_manager._lock:
                    for ds, day_data in data_manager.data.items():
                        for idx, a in enumerate(day_data.get("alerts", [])):
                            items.append(rs.alert_to_dict(a, ds, idx))
        else:
            items = _alerts_with_ids_for_date(date_str)

        if sort == "score":
            items.sort(key=lambda a: a.get("score") or 0, reverse=True)
        else:
            items.sort(
                key=lambda a: (a.get("date") or "", a.get("time") or ""),
                reverse=True,
            )
        items = items[:limit]
        return {"alerts": [AlertOut(**a).model_dump() for a in items]}

    @router.get("/api/alerts/image")
    def alert_image(path: str):
        img_dir = os.path.realpath(data_manager._img_dir)
        os.makedirs(img_dir, exist_ok=True)
        real = os.path.realpath(path)
        if not (real == img_dir or real.startswith(img_dir + os.sep)):
            raise HTTPException(403, "허용되지 않은 경로입니다.")
        if not os.path.isfile(real):
            raise HTTPException(404, "이미지를 찾을 수 없습니다.")
        return FileResponse(real, media_type="image/jpeg")

    @router.get("/api/report", response_model=ReportOut)
    def report(period: str = Query("week")):
        if period not in ("today", "week", "month"):
            raise HTTPException(400, "period는 today|week|month")
        data = rs.aggregate(data_manager, period)
        grade_times = {}
        for g in ("적정", "주의", "부적정"):
            mins = data["grade_times"].get(g, 0) // 60
            grade_times[g] = GradeExpo(minutes=mins, pct=data["grade_pcts"].get(g, 0))
        return ReportOut(
            period=period,  # type: ignore
            avg=data["avg"],
            ratio=data["ratio"],
            alerts=data["alerts"],
            avgLoad=data["avg_load"],
            duration=data["duration"],
            gradeTimes=grade_times,
            worstBadAxis=data["worst_bad_axis"],
            series=[SeriesPoint(label=l, avg=a) for l, a in data["series"]],
            problems=data["problems"],
            hasScores=data["hasScores"],
        )

    @router.get("/api/settings", response_model=SettingsOut)
    def get_settings():
        return SettingsOut(alert_interval=app_settings.alert_interval)

    @router.put("/api/settings", response_model=SettingsOut)
    def put_settings(body: SettingsIn):
        if body.alert_interval not in ALERT_INTERVALS:
            raise HTTPException(400, "허용되지 않은 알림 간격")
        app_settings.alert_interval = body.alert_interval
        if monitor.analyzer is not None:
            monitor.analyzer.alert_interval = body.alert_interval
        return SettingsOut(alert_interval=app_settings.alert_interval)

    @router.get("/api/info", response_model=InfoOut)
    def info():
        return InfoOut(
            appName="바른자세 — Posture Monitor Pro",
            version="2.1",
            dataFile=DATA_FILE,
            settingsFile=app_settings.filepath,
            alertImagesDir=data_manager._img_dir,
        )

    return router
