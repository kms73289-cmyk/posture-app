import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { ALERT_INTERVALS } from "../lib/constants";
import { useMonitorStore } from "../store/monitorStore";

export function SettingsPage() {
  const qc = useQueryClient();
  const pushToast = useMonitorStore((s) => s.pushToast);
  const settingsQ = useQuery({ queryKey: ["settings"], queryFn: api.settings });
  const infoQ = useQuery({ queryKey: ["info"], queryFn: api.info });
  const mut = useMutation({
    mutationFn: (v: number) => api.putSettings(v),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (e: Error) => pushToast(e.message),
  });
  const current = settingsQ.data?.alert_interval ?? 60;
  const info = infoQ.data;

  return (
    <div className="max-w-3xl space-y-8">
      <section>
        <h2 className="text-lg font-bold">알림 설정</h2>
        <p className="mb-3 text-sm text-ink-muted">
          자세 불량이 감지될 때 배너를 보낼 최소 간격입니다.
        </p>
        <label className="block text-sm font-semibold text-ink-muted">
          알림 간격
          <select
            className="mt-2 block w-56 rounded-xl border border-[var(--color-border)] bg-white px-4 py-3 font-bold text-primary shadow-card"
            value={current}
            onChange={(e) => mut.mutate(Number(e.target.value))}
            aria-label="알림 간격"
          >
            {ALERT_INTERVALS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      </section>
      <section className="card p-5">
        <h2 className="mb-3 text-lg font-bold">정보</h2>
        <InfoRow k="앱 이름" v={info?.appName ?? "바른자세 — Posture Monitor Pro"} />
        <InfoRow k="버전" v={info?.version ?? "2.1"} />
        <InfoRow k="데이터" v={info?.dataFile ?? "불러오는 중..."} />
        <InfoRow k="설정" v={info?.settingsFile ?? "불러오는 중..."} />
      </section>
    </div>
  );
}

function InfoRow({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-6 border-b border-[var(--color-border)] py-3 last:border-0">
      <span className="w-16 shrink-0 text-sm text-ink-muted">{k}</span>
      <span className="break-all text-sm">{v}</span>
    </div>
  );
}
