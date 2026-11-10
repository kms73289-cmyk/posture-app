import { useEffect, useRef, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Camera, Clock, Loader2, Play, Square, Trophy, RefreshCw } from "lucide-react";
import { api } from "../lib/api";
import { AXIS_ROWS, NEUTRAL_NECK_KG, TIPS, TIPS_BY_AXIS } from "../lib/constants";
import { fmtMmSs, sittingChip } from "../lib/format";
import { AXIS_LABEL, badgeClass, scoreColorVar, scoreLabel, scoreTextClass } from "../lib/grade";
import { useMonitorStore } from "../store/monitorStore";
import { ScoreRing } from "../components/ScoreRing";

export function MeasurePage() {
  const st = useMonitorStore((s) => s.state);
  const pushToast = useMonitorStore((s) => s.pushToast);
  const qc = useQueryClient();
  const [busy, setBusy] = useState<"start" | "stop" | "recal" | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [tipIdx, setTipIdx] = useState(0);
  const [streamKey, setStreamKey] = useState(0);
  const [camReady, setCamReady] = useState(false);
  const wasLive = useRef(false);

  const todayQ = useQuery({
    queryKey: ["today"],
    queryFn: api.today,
    refetchInterval: 15_000,
  });
  const today = todayQ.data;

  useEffect(() => {
    const id = window.setInterval(() => setTipIdx((i) => i + 1), 15_000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!st.running) {
      wasLive.current = false;
      setCamReady(false);
      return;
    }
    if (st.cameraOk && !wasLive.current) {
      wasLive.current = true;
      setStreamKey((k) => k + 1);
      setCamReady(true);
    }
  }, [st.running, st.cameraOk]);

  const tip = st.worstAxis && TIPS_BY_AXIS[st.worstAxis]
    ? TIPS_BY_AXIS[st.worstAxis]
    : TIPS[tipIdx % TIPS.length];

  async function onStart() {
    setBusy("start");
    setStartError(null);
    api.log({ step: 1, event: "measure_start_click" });
    try {
      api.log({ step: 2, event: "measure_start_request", url: "/api/measure/start" });
      const result = await api.start();
      api.log({ step: 3, event: "measure_start_ok", result });
    } catch (e) {
      const aborted = e instanceof DOMException && e.name === "AbortError";
      const msg = aborted
        ? "서버 응답이 없습니다. 앱을 종료한 뒤 다시 실행해 주세요."
        : e instanceof Error
          ? e.message
          : "측정을 시작하지 못했습니다.";
      api.log({ step: 3, event: "measure_start_fail", error: msg });
      setStartError(msg);
      pushToast(msg);
    } finally {
      setBusy(null);
    }
  }
  async function onStop() {
    setBusy("stop");
    try {
      await api.stop();
      await qc.invalidateQueries();
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "측정을 중지하지 못했습니다.");
    } finally {
      setBusy(null);
    }
  }
  async function onRecal() {
    setBusy("recal");
    try {
      await api.recalibrate();
    } catch (e) {
      pushToast(e instanceof Error ? e.message : "기준 재설정에 실패했습니다.");
    } finally {
      setBusy(null);
    }
  }

  const camChip = !st.running
    ? { text: "카메라 꺼짐", cls: "text-ink-hint" }
    : st.cameraOk
      ? { text: "카메라 연결됨", cls: "text-good" }
      : { text: "카메라 연결 중", cls: "text-warn" };

  const statusMsg = measureStatus(st);
  const avgToday = today?.avgScore ?? null;
  const undetected = st.running && st.calibrated && !st.detected;

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="grid shrink-0 grid-cols-3 gap-4">
        <StatCard
          icon={<Trophy size={22} className="text-primary" />}
          label="오늘 평균 등급"
          value={avgToday == null ? "--" : scoreLabel(avgToday)}
          sub={avgToday == null ? "데이터 없음" : "오늘 평균"}
          valueClass={avgToday == null ? "text-ink-hint" : scoreTextClass(avgToday)}
        />
        <StatCard
          icon={<Clock size={22} className="text-primary" />}
          label="측정 시간"
          value={st.running ? fmtMmSs(st.session.elapsedSec) : "00:00"}
          chip={sittingChip(today?.sittingSec ?? 0)}
        />
        <StatCard
          icon={<span className="text-lg">✓</span>}
          label="현재 상태"
          value={!st.running ? "오프라인" : st.gradeLabel ?? "--"}
          sub={
            st.running && st.grade && st.grade > 1 && st.worstAxis
              ? `(원인: ${AXIS_LABEL[st.worstAxis]})`
              : undefined
          }
          valueClass={!st.running ? "text-ink-hint" : scoreTextClass(st.grade)}
          goodIcon
        />
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1.35fr)_minmax(320px,0.9fr)] gap-4">
        <section className="card flex min-h-0 flex-col p-5">
          <div className="mb-3 flex shrink-0 items-center justify-between">
            <h2 className="flex items-center gap-2 text-[15px] font-bold">
              <Camera size={16} className="text-ink-muted" />
              실시간 자세 모니터링
            </h2>
            <span className={`text-[12px] font-semibold ${camChip.cls}`}>
              ● {camChip.text}
            </span>
          </div>
          <div className="relative min-h-0 w-full flex-1 overflow-hidden rounded-xl bg-[#dfe8e4]">
            <div className="absolute inset-0">
              {st.running && camReady ? (
                <img
                  key={streamKey}
                  src={`/api/video?t=${streamKey}`}
                  alt="실시간 카메라"
                  className="h-full w-full object-fill"
                />
              ) : (
                <CameraOff connecting={st.running} />
              )}
            </div>
            {st.running && st.modelLoading && st.calibrated && (
              <Overlay>
                <Loader2 className="animate-spin" /> AI 모델 로딩 중...
              </Overlay>
            )}
            {st.running && st.cameraOk && !st.calibrated && st.calibRemaining > 0 && (
              <CalibrationOverlay remaining={st.calibRemaining} />
            )}
            {undetected && (
              <p className="absolute bottom-3 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-full bg-black/45 px-3 py-1 text-center text-[13px] text-white">
                사람을 감지할 수 없습니다.
              </p>
            )}
          </div>
        </section>

        <section className="card flex min-h-0 flex-col overflow-hidden p-5">
          <h2 className="mb-3 shrink-0 text-[15px] font-bold">실시간 자세 지표</h2>
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
            {AXIS_ROWS.map((row) => {
              const ax = st.axes[row.key];
              const v = ax?.value;
              const g = ax?.grade ?? null;
              const pct = v == null ? 0 : Math.min(100, (Math.abs(v) / row.max) * 100);
              return (
                <div key={row.key}>
                  <div className="mb-1 flex items-center justify-between text-[13px]">
                    <span className="text-ink-muted">{row.label}</span>
                    <span className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${badgeClass(g)}`}>
                        {g ? scoreLabel(g) : "--"}
                      </span>
                      <span className="font-bold">
                        {v == null ? "--" : `${v.toFixed(1)}${row.unit}`}
                      </span>
                    </span>
                  </div>
                  <div className="grade-bar">
                    <span style={{ width: `${pct}%`, background: scoreColorVar(g) }} />
                  </div>
                </div>
              );
            })}
            <div className="flex items-center gap-4 pt-2">
              <ScoreRing score={st.grade} size={96} stroke={10} />
              <div>
                <p className={`text-sm font-bold ${scoreTextClass(st.grade)}`}>
                  {st.gradeLabel
                    ? `종합: ${st.gradeLabel}${st.worstAxis && st.grade && st.grade > 1 ? ` (원인: ${AXIS_LABEL[st.worstAxis]})` : ""}`
                    : "종합: --"}
                </p>
                <div className="mt-2 h-1.5 w-40 overflow-hidden rounded bg-[#E2E8F0]">
                  <div
                    className="h-full"
                    style={{
                      width: st.grade == null ? 0 : `${((3 - Math.min(3, Math.max(1, st.grade))) / 2) * 100}%`,
                      background: scoreColorVar(st.grade),
                    }}
                  />
                </div>
                <p
                  className="mt-3 text-[13px] font-bold"
                  style={{ color: scoreColorVar(st.axes.neck.grade) }}
                >
                  {st.neckLoadKg == null
                    ? "목 하중  약 --kg"
                    : `목 하중 약 ${Math.round(st.neckLoadKg)}kg (중립 대비 ${(st.neckLoadKg / NEUTRAL_NECK_KG).toFixed(1)}배)`}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-2 rounded-2xl bg-[#F7FAFC] p-3 text-center text-[12px]">
              <Mini label="경과 시간" value={fmtMmSs(st.session.elapsedSec)} />
              <Mini
                label="평균 등급"
                value={st.session.avgGrade == null ? "--" : scoreLabel(st.session.avgGrade)}
                color={scoreColorVar(st.session.avgGrade)}
              />
              <Mini
                label="최고 등급"
                value={st.session.bestGrade == null ? "--" : scoreLabel(st.session.bestGrade)}
                color={scoreColorVar(st.session.bestGrade)}
              />
            </div>
          </div>
        </section>
      </div>

      <div className="grid shrink-0 grid-cols-[minmax(0,1.35fr)_minmax(320px,0.9fr)] gap-4">
        <section className="card flex items-center justify-between gap-4 px-5 py-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${statusMsg.dot}`} />
              <p className={`font-bold ${statusMsg.cls}`}>{statusMsg.title}</p>
            </div>
            <p className="mt-1 text-[13px] text-ink-muted">
              기준 설정: 처음 5초간 바른 자세로 앉아주세요. 이후 자동으로 측정이 이어집니다.
            </p>
            {startError && !st.running && (
              <p className="mt-2 text-[13px] font-semibold text-danger">{startError}</p>
            )}
          </div>
          <div className="flex shrink-0 gap-2">
            {!st.running ? (
              <button
                type="button"
                onClick={onStart}
                disabled={busy !== null}
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white hover:bg-primary-hover disabled:opacity-60"
              >
                {busy === "start" ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
                측정 시작
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={onStop}
                  disabled={busy !== null}
                  className="inline-flex items-center gap-2 rounded-xl border border-primary px-4 py-3 text-sm font-bold text-primary disabled:opacity-60"
                >
                  {busy === "stop" ? <Loader2 size={16} className="animate-spin" /> : <Square size={14} />}
                  측정 중지
                </button>
                <button
                  type="button"
                  onClick={onRecal}
                  disabled={busy !== null}
                  className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-bold text-white hover:bg-primary-hover disabled:opacity-60"
                >
                  {busy === "recal" ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                  기준 재설정
                </button>
              </>
            )}
          </div>
        </section>
        <section className="card flex items-center gap-4 px-5 py-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--badge-good-bg)] text-xl">
            💡
          </div>
          <div className="min-w-0">
            <p className="text-[12px] font-bold text-ink-muted">자세 개선 TIP</p>
            <p className="text-[14px] font-semibold">{tip}</p>
          </div>
        </section>
      </div>
    </div>
  );
}

function measureStatus(st: ReturnType<typeof useMonitorStore.getState>["state"]) {
  if (!st.running) return { title: "오프라인", cls: "text-ink", dot: "bg-ink-hint" };
  if (!st.cameraOk)
    return { title: "카메라를 연결하는 중...", cls: "text-ink-muted", dot: "bg-warn" };
  if (st.modelLoading) return { title: "AI 모델 로딩 중...", cls: "text-ink-muted", dot: "bg-warn" };
  if (!st.calibrated)
    return {
      title: `기준 설정 중... ${st.calibRemaining}초 남음 (바르게 앉아주세요!)`,
      cls: "text-warn",
      dot: "bg-warn",
    };
  if (!st.detected)
    return { title: "사람을 감지할 수 없습니다.", cls: "text-ink-muted", dot: "bg-ink-hint" };
  if (st.gradeLabel === "주의")
    return { title: "자세가 주의 상태입니다. 바르게 앉아주세요.", cls: "text-warn", dot: "bg-warn" };
  if (st.gradeLabel === "부적정")
    return { title: "자세가 부적정합니다. 즉시 교정해주세요.", cls: "text-danger", dot: "bg-danger" };
  return {
    title: "정상적으로 측정 중입니다. 바른 자세를 유지해주세요!",
    cls: "text-good",
    dot: "bg-good",
  };
}

function StatCard({
  icon,
  label,
  value,
  sub,
  chip,
  valueClass,
  goodIcon,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  sub?: string;
  chip?: string;
  valueClass?: string;
  goodIcon?: boolean;
}) {
  return (
    <div className="card flex items-center gap-4 px-5 py-4">
      <div
        className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${goodIcon ? "bg-[var(--badge-good-bg)] text-primary" : "bg-[var(--badge-good-bg)]"}`}
      >
        {icon}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[12px] text-ink-muted">{label}</p>
        <p className={`text-[26px] font-extrabold leading-tight ${valueClass ?? ""}`}>{value}</p>
        {sub && <p className="text-[12px] text-ink-hint">{sub}</p>}
      </div>
      {chip && (
        <span className="shrink-0 rounded-full bg-[var(--nav-active-bg)] px-3 py-1 text-[11px] font-bold text-primary">
          {chip}
        </span>
      )}
    </div>
  );
}

function Mini({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <p className="text-ink-hint">{label}</p>
      <p className="text-[13px] font-bold" style={{ color }}>
        {value}
      </p>
    </div>
  );
}

function CalibrationOverlay({ remaining }: { remaining: number }) {
  const total = 5;
  const rem = Math.max(0, remaining);
  return (
    <div className="absolute left-4 right-4 top-4 z-20 rounded-xl bg-black/35 px-4 py-3 text-white">
      <p className="font-bold">바르게 앉아주세요!</p>
      <p className="text-sm opacity-90">{rem}초 남음</p>
      <div className="mt-2 h-1.5 overflow-hidden rounded bg-white/30">
        <div
          className="h-full bg-[#2dd4bf]"
          style={{ width: `${((total - rem) / total) * 100}%` }}
        />
      </div>
    </div>
  );
}

function Overlay({ children }: { children: ReactNode }) {
  return (
    <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-black/40 text-sm font-bold text-white">
      {children}
    </div>
  );
}

function CameraOff({ connecting = false }: { connecting?: boolean }) {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center text-ink-muted">
      <Camera size={48} className="mb-3 opacity-40" />
      <p className="text-sm font-semibold">
        {connecting ? "카메라를 연결하는 중..." : "측정 시작을 누르면 카메라가 켜집니다"}
      </p>
    </div>
  );
}
