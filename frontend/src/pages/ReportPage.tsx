import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import { AXIS_LABEL, scoreColorVar, scoreLabel, scoreTextClass } from "../lib/grade";
import type { PeriodKey } from "../types";

const TABS: { key: PeriodKey; label: string }[] = [
  { key: "today", label: "오늘" },
  { key: "week", label: "이번 주" },
  { key: "month", label: "이번 달" },
];

export function ReportPage() {
  const [period, setPeriod] = useState<PeriodKey>("week");
  const q = useQuery({
    queryKey: ["report", period],
    queryFn: () => api.report(period),
    refetchOnMount: "always",
  });

  const data = q.data;
  const series = (data?.series ?? []).map((s) => ({
    label: s.label,
    bar: s.avg == null ? null : (3 - Math.max(1, Math.min(3, s.avg))) / 2,
    avg: s.avg,
    fill: s.avg == null ? "#E2E8F0" : scoreColorVar(s.avg),
  }));

  return (
    <div className="space-y-5">
      <p className="text-sm text-ink-muted">기간별 자세 데이터를 분석합니다.</p>
      <div className="flex gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setPeriod(t.key)}
            className={`rounded-xl px-5 py-2 text-sm font-semibold ${
              period === t.key
                ? "bg-[var(--nav-active-bg)] text-primary ring-1 ring-primary"
                : "bg-white text-ink-muted shadow-card"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-4">
        <SumCard
          label="평균 자세 등급"
          value={data?.avg == null ? "--" : scoreLabel(data.avg)}
          cls={scoreTextClass(data?.avg ?? null)}
        />
        <SumCard
          label="바른 자세 비율"
          value={data?.ratio == null ? "--" : `${Math.round(data.ratio)}%`}
          cls={(data?.ratio ?? 0) >= 60 ? "text-good" : "text-warn"}
        />
        <SumCard
          label="경고 횟수"
          value={String(data?.alerts ?? 0)}
          cls={(data?.alerts ?? 0) > 5 ? "text-danger" : ""}
        />
        <SumCard
          label="평균 목 하중"
          value={data?.avgLoad == null ? "데이터 없음" : `약 ${Math.round(data.avgLoad)}kg`}
          cls={data?.avgLoad == null ? "text-ink-hint" : ""}
        />
      </div>
      <section className="card p-5">
        <p className="mb-3 text-sm text-ink-muted">등급 추이</p>
        <div className="h-52">
          {!data?.hasScores && (data?.series.length ?? 0) === 0 ? (
            <p className="flex h-full items-center justify-center text-ink-hint">데이터 없음</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={series}>
                <CartesianGrid strokeDasharray="4 4" vertical={false} stroke="#EDF2F7" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#718096" }} axisLine={false} tickLine={false} />
                <YAxis hide domain={[0, 1]} />
                <Tooltip
                  formatter={(_v, _n, item) => {
                    const avg = (item.payload as { avg: number | null }).avg;
                    return [avg == null ? "-" : scoreLabel(avg), "등급"];
                  }}
                />
                <Bar dataKey="bar" radius={[6, 6, 0, 0]} maxBarSize={32}>
                  {series.map((s, i) => (
                    <Cell key={i} fill={s.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </section>
      <section className="card p-5">
        <p className="mb-3 text-sm text-ink-muted">등급별 노출 시간</p>
        {(["적정", "주의", "부적정"] as const).map((g, i) => {
          const item = data?.gradeTimes[g];
          const grade = (i + 1) as 1 | 2 | 3;
          return (
            <div key={g} className="flex items-center justify-between py-1 text-sm">
              <span className="flex items-center gap-2">
                <span style={{ color: scoreColorVar(grade) }}>●</span>
                {g}
              </span>
              <span className="font-bold">
                {data?.hasScores ? `${item?.minutes ?? 0}분 (${Math.round(item?.pct ?? 0)}%)` : "데이터 없음"}
              </span>
            </div>
          );
        })}
        <p className="mt-2 text-[12px] text-ink-muted">
          {data?.worstBadAxis
            ? `부적정이 가장 많았던 축: ${AXIS_LABEL[data.worstBadAxis] ?? data.worstBadAxis}`
            : data?.hasScores
              ? "부적정 기록 없음"
              : ""}
        </p>
      </section>
      <section className="card p-5">
        <p className="mb-3 text-sm text-ink-muted">자세 상태</p>
        <div className="grid grid-cols-4 gap-3">
          {(data?.problems ?? []).map((p) => (
            <div key={p.label} className="rounded-2xl border border-[var(--color-border)] p-4">
              <p className="text-center text-sm font-bold">{p.label}</p>
              <p
                className="mt-1 text-center text-lg font-extrabold"
                style={{ color: scoreColorVar(p.statusGrade) }}
              >
                {p.status}
              </p>
              <div className="relative mt-3">
                <div className="relative mb-1 h-3">
                  {(p.ticks ?? []).map((t) => (
                    <span
                      key={`${t.label}-${t.at}`}
                      className={`absolute -translate-x-1/2 text-[10px] ${t.label === "부적정" ? "text-danger" : "text-warn"}`}
                      style={{ left: `${t.at}%` }}
                    >
                      {t.label}
                    </span>
                  ))}
                </div>
                <div className="relative h-2 overflow-hidden rounded bg-[#E5E7EB]">
                  <div
                    className="absolute inset-y-0 left-0"
                    style={{
                      width: `${p.percent}%`,
                      background: scoreColorVar(p.statusGrade),
                    }}
                  />
                  {(p.ticks ?? []).map((t) => (
                    <span
                      key={`tick-${t.label}-${t.at}`}
                      className={`absolute inset-y-0 w-px ${t.label === "부적정" ? "bg-danger" : "bg-warn"}`}
                      style={{ left: `${t.at}%` }}
                    />
                  ))}
                </div>
              </div>
              <p className="mt-2 text-center text-sm font-bold" style={{ color: scoreColorVar(p.statusGrade) }}>
                {p.percent}%
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function SumCard({ label, value, cls }: { label: string; value: string; cls: string }) {
  return (
    <div className="card p-5">
      <p className="text-[12px] text-ink-muted">{label}</p>
      <p className={`mt-1 text-2xl font-extrabold ${cls}`}>{value}</p>
    </div>
  );
}
