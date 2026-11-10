export type AxisKey = "neck" | "forward" | "lateral" | "shoulder";
export type PeriodKey = "today" | "week" | "month";
export type SortKey = "time" | "score";

export interface AxisState {
  value: number | null;
  unit: string;
  grade: number | null;
}

export interface SessionState {
  elapsedSec: number;
  avgGrade: number | null;
  bestGrade: number | null;
}

export interface BannerState {
  show: boolean;
  grade: number | null;
  message: string;
  sub: string;
}

export interface MonitorState {
  running: boolean;
  modelLoading: boolean;
  cameraOk: boolean;
  detected: boolean;
  calibrated: boolean;
  calibRemaining: number;
  grade: number | null;
  gradeLabel: string | null;
  worstAxis: AxisKey | null;
  axes: Record<AxisKey, AxisState>;
  neckLoadKg: number | null;
  session: SessionState;
  banner: BannerState;
}

export const EMPTY_MONITOR: MonitorState = {
  running: false,
  modelLoading: false,
  cameraOk: false,
  detected: false,
  calibrated: false,
  calibRemaining: 0,
  grade: null,
  gradeLabel: null,
  worstAxis: null,
  axes: {
    neck: { value: null, unit: "°", grade: null },
    forward: { value: null, unit: "cm", grade: null },
    lateral: { value: null, unit: "°", grade: null },
    shoulder: { value: null, unit: "°", grade: null },
  },
  neckLoadKg: null,
  session: { elapsedSec: 0, avgGrade: null, bestGrade: null },
  banner: { show: false, grade: null, message: "", sub: "" },
};

export interface HourlyPoint {
  hour: number;
  avg: number | null;
}

export interface TodayOut {
  date: string;
  weekday: string;
  sittingSec: number;
  avgScore: number | null;
  goodPostureSec: number;
  alertCount: number;
  scoreCount: number;
  badCount: number;
  totalDuration: number;
  goodRatioPct: number | null;
  badPct: number | null;
  hourly: HourlyPoint[];
}

export interface MonthDayOut {
  day: number;
  date: string;
  avgScore: number;
  totalDuration: number;
  goodPostureSec: number;
  alertCount: number;
  scoreCount: number;
}

export interface DaySummaryOut {
  date: string;
  hasData: boolean;
  avgScore: number | null;
  goodRatioPct: number | null;
  alertCount: number;
  totalDuration: number;
  goodPostureSec: number;
}

export interface AlertOut {
  id: string;
  date: string;
  time: string;
  message: string;
  severity: string;
  score: number | null;
  img_path: string | null;
  axis1: number | null;
  axis2: number | null;
  axis3: number | null;
  axis4: number | null;
  worst_axis: string | null;
  neck_flexion: number | null;
  neck_load_kg: number | null;
  forward_dist: number | null;
  lateral_tilt: number | null;
  shoulder_tilt: number | null;
  mainProblem: string;
}

export interface SeriesPoint {
  label: string;
  avg: number | null;
}

export interface ProblemTick {
  at: number;
  label: string;
}

export interface ProblemCard {
  label: string;
  value: number;
  percent: number;
  max: number;
  status: string;
  statusGrade: number;
  ticks?: ProblemTick[];
}

export interface GradeExpo {
  minutes: number;
  pct: number;
}

export interface ReportOut {
  period: PeriodKey;
  avg: number | null;
  ratio: number | null;
  alerts: number;
  avgLoad: number | null;
  duration: number;
  gradeTimes: Record<string, GradeExpo>;
  worstBadAxis: string | null;
  series: SeriesPoint[];
  problems: ProblemCard[];
  hasScores: boolean;
}

export interface SettingsOut {
  alert_interval: number;
}

export interface InfoOut {
  appName: string;
  version: string;
  dataFile: string;
  settingsFile: string;
  alertImagesDir: string;
}
