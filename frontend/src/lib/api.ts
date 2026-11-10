import type {
  AlertOut,
  DaySummaryOut,
  InfoOut,
  MonthDayOut,
  PeriodKey,
  ReportOut,
  SettingsOut,
  TodayOut,
} from "../types";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `요청 실패 (${res.status})`;
    try {
      const b = await res.json();
      if (b?.detail) msg = typeof b.detail === "string" ? b.detail : msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return res.json() as Promise<T>;
}

function req<T>(url: string, init?: RequestInit): Promise<T> {
  return fetch(url, init).then((r) => json<T>(r));
}

function timedReq<T>(url: string, init: RequestInit, ms: number): Promise<T> {
  const ctrl = new AbortController();
  const t = window.setTimeout(() => ctrl.abort(), ms);
  return req<T>(url, { ...init, signal: ctrl.signal }).finally(() => window.clearTimeout(t));
}

export const api = {
  start: () => timedReq("/api/measure/start", { method: "POST" }, 60_000),
  stop: () => timedReq("/api/measure/stop", { method: "POST" }, 15_000),
  recalibrate: () => timedReq("/api/measure/recalibrate", { method: "POST" }, 15_000),
  today: () => req<TodayOut>("/api/today"),
  month: (year: number, month: number) =>
    req<{ year: number; month: number; days: MonthDayOut[] }>(
      `/api/month?year=${year}&month=${month}`,
    ),
  day: (date: string) => req<DaySummaryOut>(`/api/day?date=${date}`),
  alerts: (params: { date?: string; sort?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params.date) q.set("date", params.date);
    if (params.sort) q.set("sort", params.sort);
    if (params.limit) q.set("limit", String(params.limit));
    return req<{ alerts: AlertOut[] }>(`/api/alerts?${q}`);
  },
  alertImageUrl: (path: string) => `/api/alerts/image?path=${encodeURIComponent(path)}`,
  report: (period: PeriodKey) => req<ReportOut>(`/api/report?period=${period}`),
  settings: () => req<SettingsOut>("/api/settings"),
  putSettings: (alert_interval: number) =>
    req<SettingsOut>("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alert_interval }),
    }),
  info: () => req<InfoOut>("/api/info"),
};
