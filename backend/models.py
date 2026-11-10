"""프론트 `types.ts`와 동일한 형태의 Pydantic 모델."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

AxisKey = Literal["neck", "forward", "lateral", "shoulder"]
PeriodKey = Literal["today", "week", "month"]
SortKey = Literal["time", "score"]


class AxisState(BaseModel):
    value: Optional[float] = None
    unit: str
    grade: Optional[int] = None


class SessionState(BaseModel):
    elapsedSec: int = 0
    avgGrade: Optional[float] = None
    bestGrade: Optional[int] = None


class BannerState(BaseModel):
    show: bool = False
    grade: Optional[int] = None
    message: str = ""
    sub: str = ""


class MonitorState(BaseModel):
    running: bool = False
    modelLoading: bool = False
    cameraOk: bool = False
    detected: bool = False
    calibrated: bool = False
    calibRemaining: int = 0
    grade: Optional[int] = None
    gradeLabel: Optional[str] = None
    worstAxis: Optional[AxisKey] = None
    axes: dict[str, AxisState]
    neckLoadKg: Optional[float] = None
    session: SessionState = Field(default_factory=SessionState)
    banner: BannerState = Field(default_factory=BannerState)


class SettingsIn(BaseModel):
    alert_interval: int


class SettingsOut(BaseModel):
    alert_interval: int


class InfoOut(BaseModel):
    appName: str
    version: str
    dataFile: str
    settingsFile: str
    alertImagesDir: str


class HourlyPoint(BaseModel):
    hour: int
    avg: Optional[float] = None


class TodayOut(BaseModel):
    date: str
    weekday: str
    sittingSec: int = 0
    avgScore: Optional[float] = None
    goodPostureSec: int = 0
    alertCount: int = 0
    scoreCount: int = 0
    badCount: int = 0
    totalDuration: int = 0
    goodRatioPct: Optional[int] = None
    badPct: Optional[float] = None
    hourly: list[HourlyPoint]


class MonthDayOut(BaseModel):
    day: int
    date: str
    avgScore: float
    totalDuration: int
    goodPostureSec: int
    alertCount: int
    scoreCount: int


class DaySummaryOut(BaseModel):
    date: str
    hasData: bool
    avgScore: Optional[float] = None
    goodRatioPct: Optional[int] = None
    alertCount: int = 0
    totalDuration: int = 0
    goodPostureSec: int = 0


class AlertOut(BaseModel):
    id: str
    date: str
    time: str
    message: str
    severity: str
    score: Optional[int] = None
    img_path: Optional[str] = None
    axis1: Optional[int] = None
    axis2: Optional[int] = None
    axis3: Optional[int] = None
    axis4: Optional[int] = None
    worst_axis: Optional[str] = None
    neck_flexion: Optional[float] = None
    neck_load_kg: Optional[float] = None
    forward_dist: Optional[float] = None
    lateral_tilt: Optional[float] = None
    shoulder_tilt: Optional[float] = None
    mainProblem: str


class SeriesPoint(BaseModel):
    label: str
    avg: Optional[float] = None


class ProblemTick(BaseModel):
    at: float
    label: str


class ProblemCard(BaseModel):
    label: str
    value: float
    percent: int
    max: float
    status: str
    statusGrade: int  # 1 적정 / 2 주의 / 3 부적정
    ticks: list[ProblemTick] = []


class GradeExpo(BaseModel):
    minutes: int
    pct: float


class ReportOut(BaseModel):
    period: PeriodKey
    avg: Optional[float] = None
    ratio: Optional[float] = None
    alerts: int = 0
    avgLoad: Optional[float] = None
    duration: int = 0
    gradeTimes: dict[str, GradeExpo]
    worstBadAxis: Optional[str] = None
    series: list[SeriesPoint]
    problems: list[ProblemCard]
    hasScores: bool = False
