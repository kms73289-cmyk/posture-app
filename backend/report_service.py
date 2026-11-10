"""ui/report.py 집계 로직을 UI 없이 이식. 임계값·정렬은 원본과 동일."""
from __future__ import annotations

import math
from datetime import date, timedelta

from config import SCORE_INTERVAL, score_grade

# ui/report.py _WORST_AXIS_KO
WORST_AXIS_KO = {
    "neck": "목 굴곡",
    "forward": "머리 앞돌출",
    "lateral": "측방 기울기",
    "shoulder": "어깨 기울기",
}

# ui/history.py / ui/alerts.py 축 최대값 (기록 페이지 주요 문제 비율용 — 변경하지 않음)
AXIS_MAX = {
    "neck_flexion": 30.0,
    "forward_dist": 15.0,
    "lateral_tilt": 20.0,
    "shoulder_tilt": 12.0,
}

# analyzer.py _judge_axes 와 동일 (산출식은 analyzer가 담당, 분석 카드 표시만 이 임계 사용)
# 목 굴곡: ≤10 적정 / ≤20 주의 / >20 부적정
# 측방: ≤10 적정 / >10 부적정
# 어깨: ≤10 적정 / ≤20 주의 / >20 부적정
# 앞돌출: SPC(세션 기준) — 알림에 저장된 axis2 등급 재사용
NECK_GOOD = 10.0
NECK_WARN = 20.0
LATERAL_GOOD = 10.0
SHOULDER_GOOD = 10.0
SHOULDER_WARN = 20.0
# 거북목(앞돌출)은 analyzer와 같이 2단계: 적정 / 부적정 (주의 없음)
FORWARD_MAX_CM = 15.0
FORWARD_BAD_CM = FORWARD_MAX_CM * 0.70  # 원본 분석 바 위험선 10.5cm

# ui/dashboard.py 부적정 노출 게이지
BAD_PCT_GOOD = 20
BAD_PCT_WARN = 50

# ui/dashboard.py 시간대 차트
DASHBOARD_HOURS = list(range(8, 21))

PROBLEM_AXES = [
    ("목 굴곡", "neck_flexion", 30.0),
    ("머리 앞돌출", "forward_dist", 15.0),
    ("측방 기울기", "lateral_tilt", 20.0),
    ("어깨 기울기", "shoulder_tilt", 12.0),
]


def get_date_range(period: str) -> list[date]:
    """오늘=1일, 주=오늘 포함 최근 7일, 달=1일~오늘. report.py _get_date_range."""
    today = date.today()
    if period == "today":
        return [today]
    if period == "week":
        return [today - timedelta(days=i) for i in range(6, -1, -1)]
    days, d = [], date(today.year, today.month, 1)
    while d.month == today.month and d <= today:
        days.append(d)
        d += timedelta(days=1)
    return days


def psi_status_label(grade: int) -> str:
    """config.score_grade 와 동일: 1 적정 / 2 주의 / 3 부적정."""
    if grade <= 1:
        return "적정"
    if grade <= 2:
        return "주의"
    return "부적정"


def _judge_neck(v: float) -> int:
    if v <= NECK_GOOD:
        return 1
    if v <= NECK_WARN:
        return 2
    return 3


def _judge_lateral(v: float) -> int:
    return 1 if v <= LATERAL_GOOD else 3


def _judge_shoulder(v: float) -> int:
    if v <= SHOULDER_GOOD:
        return 1
    if v <= SHOULDER_WARN:
        return 2
    return 3


def _judge_forward_cm(v: float) -> int:
    """거북목(앞돌출). 주의 없이 적정(1) / 부적정(3)."""
    return 1 if v < FORWARD_BAD_CM else 3


def _axis_ticks(kind: str, max_value: float) -> list[dict]:
    def at(threshold: float, label: str) -> dict:
        return {"at": min(100.0, threshold / max_value * 100.0), "label": label}

    if kind == "neck":
        return [at(NECK_GOOD, "주의"), at(NECK_WARN, "부적정")]
    if kind == "shoulder":
        return [at(SHOULDER_GOOD, "주의"), at(SHOULDER_WARN, "부적정")]
    if kind == "lateral":
        return [at(LATERAL_GOOD, "부적정")]
    if kind == "forward":
        return [at(FORWARD_BAD_CM, "부적정")]
    return []


REPORT_PROBLEM_AXES = [
    # (표시명, 스냅샷 키, 축 등급 키, 바 최대, 판정 종류)
    # 목·어깨: analyzer 10°/20°. 바 최대 30°로 눈금이 겹치지 않게 표시.
    # 거북목: 주의 없음. 부적정만 15cm 바의 70%(10.5cm)
    ("목 굴곡", "neck_flexion", "axis1", 30.0, "neck"),
    ("머리 앞돌출", "forward_dist", "axis2", 15.0, "forward"),
    ("측방 기울기", "lateral_tilt", "axis3", 20.0, "lateral"),
    ("어깨 기울기", "shoulder_tilt", "axis4", 30.0, "shoulder"),
]


def get_top_problems(data_manager, dates: list[date]) -> list[dict]:
    """알림 스냅샷 평균값 + analyzer.py 축 임계값으로 적정/주의/부적정 판정."""
    result = []
    for label, key, _axis_key, max_value, kind in REPORT_PROBLEM_AXES:
        values = []
        for d in dates:
            alerts = data_manager.get_day_alerts(d.isoformat())
            for alert in alerts:
                value = alert.get(key)
                if value is not None:
                    try:
                        v = abs(float(value))
                        if not math.isnan(v):
                            values.append(v)
                    except (TypeError, ValueError):
                        pass
        if values:
            avg_value = sum(values) / len(values)
            percent = min(100, int((avg_value / max_value) * 100))
        else:
            avg_value = 0
            percent = 0
        if not values:
            status_grade = 1
        elif kind == "forward":
            status_grade = _judge_forward_cm(avg_value)
        elif kind == "neck":
            status_grade = _judge_neck(avg_value)
        elif kind == "lateral":
            status_grade = _judge_lateral(avg_value)
        else:
            status_grade = _judge_shoulder(avg_value)
        result.append({
            "label": label,
            "value": round(avg_value, 1),
            "percent": percent,
            "max": max_value,
            "status": psi_status_label(status_grade),
            "statusGrade": status_grade,
            "ticks": _axis_ticks(kind, max_value),
        })
    result.sort(key=lambda x: x["percent"], reverse=True)
    return result


def aggregate(data_manager, period: str) -> dict:
    """ui/report.py _aggregate + _get_daily_series."""
    dates = get_date_range(period)
    all_scores, total_dur, total_alerts = [], 0, 0
    grade_counts = {"적정": 0, "주의": 0, "부적정": 0}
    hourly_raw = {}
    load_vals = []
    bad_axis_counts = {}

    for d in dates:
        d_str = d.isoformat()
        summary = data_manager.get_day_summary(d_str)
        if summary:
            for session in summary["sessions"]:
                for entry in session.get("scores", []):
                    sc = entry["score"]
                    all_scores.append(sc)
                    g, _ = score_grade(sc)
                    grade_counts[g] = grade_counts.get(g, 0) + 1
                    nl = entry.get("neck_load_kg")
                    if nl is not None:
                        load_vals.append(nl)
                    if sc == 3:
                        wa = entry.get("worst_axis")
                        if wa is not None:
                            bad_axis_counts[wa] = bad_axis_counts.get(wa, 0) + 1
            total_dur += summary["total_duration"]
            total_alerts += summary["alert_count"]
        for h, sc in data_manager.get_hourly_scores(d_str).items():
            hourly_raw.setdefault(h, []).append(sc)

    avg = sum(all_scores) / len(all_scores) if all_scores else None
    good_cnt = sum(1 for sc in all_scores if sc == 1)
    ratio = good_cnt / len(all_scores) * 100 if all_scores else None
    total_cnt = sum(grade_counts.values())
    grade_times = {g: cnt * SCORE_INTERVAL for g, cnt in grade_counts.items()}
    grade_pcts = {g: (cnt / total_cnt * 100 if total_cnt else 0) for g, cnt in grade_counts.items()}
    avg_load = sum(load_vals) / len(load_vals) if load_vals else None
    worst_bad_axis = (
        max(bad_axis_counts, key=bad_axis_counts.get) if bad_axis_counts else None
    )

    return {
        "period": period,
        "avg": avg,
        "duration": total_dur,
        "ratio": ratio,
        "alerts": total_alerts,
        "grade_counts": grade_counts,
        "grade_times": grade_times,
        "grade_pcts": grade_pcts,
        "grade_total": total_cnt,
        "avg_load": avg_load,
        "worst_bad_axis": worst_bad_axis,
        "hourly": {h: sum(v) / len(v) for h, v in hourly_raw.items()},
        "problems": get_top_problems(data_manager, dates),
        "series": get_daily_series(data_manager, period),
        "hasScores": bool(all_scores),
    }


def get_daily_series(data_manager, period: str) -> list[tuple[str, float | None]]:
    """ui/report.py _get_daily_series."""
    today = date.today()
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    if period == "today":
        h_data = data_manager.get_hourly_scores(today.isoformat())
        return [(f"{h}시", v) for h, v in sorted(h_data.items())]
    dates = get_date_range(period)
    result = []
    for d in dates:
        summary = data_manager.get_day_summary(d.isoformat())
        avg = summary["avg_score"] if summary else None
        if period == "week":
            label = "오늘" if d == today else day_names[d.weekday()]
        else:
            label = str(d.day)
        result.append((label, avg))
    return result


def main_problem(alert: dict) -> str:
    """ui/history.py _get_main_problem."""
    problems = []
    for name, key, max_value in PROBLEM_AXES:
        value = alert.get(key)
        if value is None:
            continue
        try:
            ratio = abs(float(value)) / max_value
        except (TypeError, ValueError):
            continue
        problems.append((ratio, name))
    if not problems:
        return alert.get("message") or "-"
    problems.sort(reverse=True)
    return problems[0][1]


def _finite(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


def alert_to_dict(alert: dict, date_str: str, idx: int) -> dict:
    keys = (
        "time", "message", "severity", "score", "img_path",
        "axis1", "axis2", "axis3", "axis4", "worst_axis",
        "neck_flexion", "neck_load_kg", "forward_dist", "lateral_tilt", "shoulder_tilt",
    )
    out = {k: _finite(alert.get(k)) for k in keys}
    out["id"] = f"{date_str}-{idx}"
    out["date"] = date_str
    out["mainProblem"] = main_problem(alert)
    if out.get("time") is None:
        out["time"] = "--"
    if out.get("message") is None:
        out["message"] = ""
    if out.get("severity") is None:
        out["severity"] = "info"
    return out
