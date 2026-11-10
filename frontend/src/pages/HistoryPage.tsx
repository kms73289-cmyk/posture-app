import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ALERTS_PER_PAGE } from "../lib/constants";
import { fmtDurationCompact, fmtDurationKo, formatDateKo } from "../lib/format";
import { AXIS_LABEL, scoreColorVar, scoreLabel, scoreTextClass } from "../lib/grade";
import { ScoreRing } from "../components/ScoreRing";
import type { AlertOut, DaySummaryOut, MonthDayOut } from "../types";

export function HistoryPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [selected, setSelected] = useState<string | null>(null);
  const [sort, setSort] = useState<"time" | "score">("time");
  const [scope, setScope] = useState<"day" | "all">("day");
  const [page, setPage] = useState(0);
  const [detail, setDetail] = useState<AlertOut | null>(null);

  const monthQ = useQuery({
    queryKey: ["month", year, month],
    queryFn: () => api.month(year, month),
  });
  const dayQ = useQuery({
    queryKey: ["day", selected],
    queryFn: () => api.day(selected!),
    enabled: Boolean(selected),
  });
  const alertsQ = useQuery({
    queryKey: ["alerts", scope, selected, sort],
    queryFn: () =>
      api.alerts({
        date: scope === "all" ? undefined : selected ?? undefined,
        sort,
        limit: scope === "all" ? 100 : 500,
      }),
    enabled: scope === "all" || Boolean(selected),
  });

  const byDay = useMemo(() => {
    const m = new Map<number, MonthDayOut>();
    for (const d of monthQ.data?.days ?? []) m.set(d.day, d);
    return m;
  }, [monthQ.data]);

  const alerts = alertsQ.data?.alerts ?? [];
  const maxPage = Math.max(0, Math.ceil(alerts.length / ALERTS_PER_PAGE) - 1);
  const slice = alerts.slice(page * ALERTS_PER_PAGE, page * ALERTS_PER_PAGE + ALERTS_PER_PAGE);

  function prevMonth() {
    if (month === 1) {
      setMonth(12);
      setYear((y) => y - 1);
    } else setMonth((m) => m - 1);
  }
  function nextMonth() {
    if (month === 12) {
      setMonth(1);
      setYear((y) => y + 1);
    } else setMonth((m) => m + 1);
  }

  const weeks = buildWeeks(year, month);
  const todayIso = new Date().toISOString().slice(0, 10);

  return (
    <div className="space-y-5">
      <p className="text-sm text-ink-muted">날짜를 선택하면 해당 날짜의 기록을 확인할 수 있습니다.</p>
      <div className="grid grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)] gap-4">
        <section className="card p-4">
          <div className="mb-3 flex items-center">
            <button type="button" aria-label="이전 달" className="px-3 py-1 text-ink-muted" onClick={prevMonth}>
              ‹
            </button>
            <h2 className="flex-1 text-center text-lg font-bold">
              {year}년  {month}월
            </h2>
            <button type="button" aria-label="다음 달" className="px-3 py-1 text-ink-muted" onClick={nextMonth}>
              ›
            </button>
          </div>
          <div className="mb-2 flex gap-4 text-[12px] text-ink-muted">
            <span className="text-good">● 적정</span>
            <span className="text-warn">● 주의</span>
            <span className="text-danger">● 부적정</span>
          </div>
          <div className="grid grid-cols-7 gap-1 text-center text-[12px] font-bold">
            {["월", "화", "수", "목", "금", "토", "일"].map((d, i) => (
              <div key={d} className={i >= 5 ? "text-danger" : "text-ink-muted"}>
                {d}
              </div>
            ))}
          </div>
          <div className="mt-1 grid grid-cols-7 gap-1">
            {weeks.flat().map((day, i) => {
              if (!day) return <div key={i} className="h-[72px]" />;
              const iso = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
              const rec = byDay.get(day);
              const isSel = selected === iso;
              const isToday = iso === todayIso;
              return (
                <button
                  key={iso}
                  type="button"
                  onClick={() => {
                    setSelected(iso);
                    setPage(0);
                    setScope("day");
                  }}
                  className={`h-[72px] rounded-xl border p-1 text-left ${
                    isSel
                      ? "border-primary bg-[var(--nav-active-bg)]"
                      : isToday
                        ? "border-[#B7E4D4] bg-white"
                        : "border-[var(--color-border)] bg-white"
                  }`}
                >
                  <span className={`text-[12px] font-bold ${i % 7 >= 5 ? "text-danger" : ""}`}>{day}</span>
                  {rec && (
                    <div className="mt-1 text-center">
                      <p className="text-[12px] font-bold" style={{ color: scoreColorVar(rec.avgScore) }}>
                        {scoreLabel(rec.avgScore)}
                      </p>
                      <p className="text-[10px] text-ink-hint">{fmtDurationCompact(rec.totalDuration)}</p>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </section>
        <section className="card p-5">
          {!selected ? (
            <p className="flex h-full items-center justify-center text-ink-hint">날짜를 선택하세요</p>
          ) : (
            <>
              <h3 className="mb-4 text-lg font-bold">{formatDateKo(selected)}</h3>
              {!dayQ.data?.hasData ? (
                <p className="text-ink-hint">해당 날짜의 기록이 없습니다.</p>
              ) : (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <MiniCard
                      title="평균 자세 등급"
                      value={scoreLabel(dayQ.data.avgScore)}
                      cls={scoreTextClass(dayQ.data.avgScore)}
                    />
                    <MiniCard
                      title="바른 자세 비율"
                      value={`${dayQ.data.goodRatioPct ?? 0}%`}
                      cls={(dayQ.data.goodRatioPct ?? 0) >= 60 ? "text-good" : "text-warn"}
                    />
                    <MiniCard
                      title="경고 횟수"
                      value={`${dayQ.data.alertCount}회`}
                      cls={dayQ.data.alertCount > 0 ? "text-danger" : "text-ink-muted"}
                    />
                    <MiniCard title="총 착석 시간" value={fmtDurationKo(dayQ.data.totalDuration)} />
                  </div>
                  <DayFill data={dayQ.data} />
                </>
              )}
            </>
          )}
        </section>
      </div>

      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold">알림 기록</h2>
          <div className="flex flex-wrap gap-2">
            <Toggle
              a="최근순"
              b="나쁜 자세 순"
              on={sort === "time"}
              set={(v) => {
                setSort(v ? "time" : "score");
                setPage(0);
              }}
            />
            <Toggle
              a="선택한 날짜"
              b="전체 알림(최대 100개)"
              on={scope === "day"}
              set={(v) => {
                setScope(v ? "day" : "all");
                setPage(0);
              }}
            />
          </div>
        </div>
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-[#F8FAFC] text-left text-ink">
              <tr>
                {["No", "시간", "자세 상태", "주요 문제", "상세 보기"].map((h) => (
                  <th key={h} className="px-4 py-3 font-bold">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {scope === "day" && !selected ? (
                <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-ink-hint">
                    날짜를 선택하세요
                  </td>
                </tr>
              ) : slice.length === 0 ? (
                <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-ink-hint">
                    알림 기록이 없습니다.
                  </td>
                </tr>
              ) : (
                slice.map((a, i) => (
                  <tr key={a.id} className="border-t border-[var(--color-border)]">
                    <td className="px-4 py-3 text-ink-muted">{page * ALERTS_PER_PAGE + i + 1}</td>
                    <td className="px-4 py-3">
                      {scope === "all" ? `${a.date} ${a.time}` : a.time}
                    </td>
                    <td className={`px-4 py-3 font-bold ${scoreTextClass(a.score)}`}>{scoreLabel(a.score)}</td>
                    <td className="px-4 py-3">{a.mainProblem}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="font-bold text-primary"
                        onClick={() => setDetail(a)}
                      >
                        상세 보기 &gt;
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center justify-center gap-3">
          <button
            type="button"
            aria-label="이전 페이지"
            className="rounded-lg bg-[#E2E8F0] px-3 py-1"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            ‹
          </button>
          <span className="min-w-[2rem] text-center font-bold text-primary">{page + 1}</span>
          <button
            type="button"
            aria-label="다음 페이지"
            className="rounded-lg bg-[#E2E8F0] px-3 py-1"
            onClick={() => setPage((p) => Math.min(maxPage, p + 1))}
          >
            ›
          </button>
        </div>
      </section>

      {detail && <AlertModal alert={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

function Toggle({
  a,
  b,
  on,
  set,
}: {
  a: string;
  b: string;
  on: boolean;
  set: (v: boolean) => void;
}) {
  return (
    <div className="flex rounded-xl bg-white p-1 shadow-card text-[12px]">
      <button
        type="button"
        className={`rounded-lg px-3 py-1 font-semibold ${on ? "bg-[var(--nav-active-bg)] text-primary" : "text-ink-muted"}`}
        onClick={() => set(true)}
      >
        {a}
      </button>
      <button
        type="button"
        className={`rounded-lg px-3 py-1 font-semibold ${!on ? "bg-[var(--nav-active-bg)] text-primary" : "text-ink-muted"}`}
        onClick={() => set(false)}
      >
        {b}
      </button>
    </div>
  );
}

function dayInsight(d: DaySummaryOut): string {
  const ratio = d.goodRatioPct ?? 0;
  if (d.alertCount === 0 && ratio >= 70) {
    return "경고 없이 바른 자세를 잘 유지한 날입니다.";
  }
  if ((d.avgScore ?? 1) >= 3) {
    return "부적정 기록이 많습니다. 모니터 높이와 턱 위치를 점검해 보세요.";
  }
  if ((d.avgScore ?? 1) >= 2) {
    return "주의 구간이 있었습니다. 쉬는 시간에 스트레칭을 더해 보세요.";
  }
  if (ratio >= 60) {
    return "바른 자세 비율이 양호합니다. 이 페이스를 유지해 보세요.";
  }
  return "착석 중 자세가 자주 무너졌습니다. 아래 알림 기록을 확인해 보세요.";
}

function DayFill({ data }: { data: DaySummaryOut }) {
  const ratio = data.goodRatioPct ?? 0;
  return (
    <div className="mt-4 rounded-2xl bg-[#F7FAFC] p-4">
      <div className="flex items-center gap-4">
        <ScoreRing
          percent={ratio}
          percentColor={ratio >= 60 ? "var(--color-good)" : "var(--color-warn)"}
          size={96}
          stroke={10}
        />
        <div className="min-w-0 flex-1">
          <p className="text-[12px] font-bold text-ink">바른 자세 유지 시간</p>
          <p className="mt-1 text-xl font-extrabold text-ink">{fmtDurationKo(data.goodPostureSec)}</p>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#E5E7EB]">
            <div
              className="h-full rounded-full"
              style={{
                width: `${ratio}%`,
                background: ratio >= 60 ? "var(--color-good)" : "var(--color-warn)",
              }}
            />
          </div>
          <p className="mt-3 text-[13px] leading-relaxed text-ink-muted">{dayInsight(data)}</p>
        </div>
      </div>
    </div>
  );
}

function MiniCard({ title, value, cls }: { title: string; value: string; cls?: string }) {
  return (
    <div className="rounded-2xl bg-[#F7FAFC] p-4">
      <p className="text-[12px] font-bold text-ink">{title}</p>
      <p className={`mt-2 text-2xl font-extrabold ${cls ?? ""}`}>{value}</p>
    </div>
  );
}

function AlertModal({ alert, onClose }: { alert: AlertOut; onClose: () => void }) {
  const [imgErr, setImgErr] = useState(false);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      role="presentation"
    >
      <div
        role="dialog"
        aria-label="자세 상세 기록"
        className="max-h-[90vh] w-[600px] overflow-y-auto rounded-2xl bg-white p-6 shadow-card"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-bold">자세 상세 기록</h3>
        <div className="mt-4 flex min-h-[180px] items-center justify-center rounded-xl bg-[#F7FAFC]">
          {alert.img_path && !imgErr ? (
            <img
              src={api.alertImageUrl(alert.img_path)}
              alt="알림 스냅샷"
              className="max-h-[260px] rounded-xl object-contain"
              onError={() => setImgErr(true)}
            />
          ) : (
            <p className="text-ink-hint">
              {alert.img_path ? "사진을 불러올 수 없습니다." : "저장된 사진이 없습니다."}
            </p>
          )}
        </div>
        <p className="mt-4 text-sm text-ink-muted">{alert.message}</p>
        <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
          <Row k="목 굴곡" v={fmtNum(alert.neck_flexion, "°")} />
          <Row k="앞돌출" v={fmtNum(alert.forward_dist, "cm")} />
          <Row k="측방" v={fmtNum(alert.lateral_tilt, "°")} />
          <Row k="어깨" v={fmtNum(alert.shoulder_tilt, "°")} />
          <Row k="목 하중" v={fmtNum(alert.neck_load_kg, "kg")} />
          <Row k="원인 축" v={alert.worst_axis ? AXIS_LABEL[alert.worst_axis] ?? alert.worst_axis : "--"} />
        </div>
        <button
          type="button"
          className="mt-5 w-full rounded-xl bg-primary py-2 font-bold text-white"
          onClick={onClose}
        >
          닫기
        </button>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between rounded-lg bg-[#F7FAFC] px-3 py-2">
      <span className="text-ink-muted">{k}</span>
      <span className="font-bold">{v}</span>
    </div>
  );
}

function fmtNum(v: number | null, unit: string) {
  if (v == null) return "--";
  return `${Number(v).toFixed(1)}${unit}`;
}

function buildWeeks(year: number, month: number): (number | null)[][] {
  const first = new Date(year, month - 1, 1);
  let start = first.getDay() - 1;
  if (start < 0) start = 6;
  const days = new Date(year, month, 0).getDate();
  const cells: (number | null)[] = Array(start).fill(null);
  for (let d = 1; d <= days; d++) cells.push(d);
  while (cells.length % 7) cells.push(null);
  const weeks: (number | null)[][] = [];
  for (let i = 0; i < cells.length; i += 7) weeks.push(cells.slice(i, i + 7));
  return weeks;
}
