import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Bell, User } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import { useMonitorStore } from "../../store/monitorStore";
import { scoreLabel, scoreTextClass, severityLabel } from "../../lib/grade";

const TITLES: Record<string, string> = {
  "/": "자세 측정",
  "/report": "자세 분석",
  "/history": "기록",
  "/settings": "설정",
};

export function Header() {
  const loc = useLocation();
  const title = TITLES[loc.pathname] ?? "바른자세";
  const lastAlertAt = useMonitorStore((s) => s.lastAlertAt);
  const running = useMonitorStore((s) => s.state.running);
  const [open, setOpen] = useState(false);
  const [seenAt, setSeenAt] = useState(Date.now());
  const wrap = useRef<HTMLDivElement>(null);
  const unread = running && lastAlertAt > seenAt;

  const { data } = useQuery({
    queryKey: ["alerts", "today", lastAlertAt],
    queryFn: () => api.alerts({ date: "today", sort: "time", limit: 8 }),
    enabled: open,
  });

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  return (
    <header className="flex shrink-0 items-start justify-between px-8 pb-2 pt-6">
      <div>
        <p className="text-[13px] text-ink-muted">안녕하세요!</p>
        <h1 className="text-[28px] font-extrabold tracking-tight text-ink">{title}</h1>
      </div>
      <div className="flex items-center gap-3" ref={wrap}>
        <button
          type="button"
          aria-label="알림"
          className="relative flex h-10 w-10 items-center justify-center rounded-full bg-white shadow-card"
          onClick={() => {
            setOpen((v) => !v);
            setSeenAt(Date.now());
          }}
        >
          <Bell size={18} className="text-ink-muted" />
          {unread && (
            <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-danger" />
          )}
        </button>
        {open && (
          <div className="absolute right-20 top-16 z-40 w-80 overflow-hidden rounded-2xl bg-white shadow-card">
            <p className="border-b border-[var(--color-border)] px-4 py-3 text-sm font-bold">
              오늘의 알림
            </p>
            <ul className="max-h-80 overflow-y-auto">
              {(data?.alerts ?? []).length === 0 && (
                <li className="px-4 py-8 text-center text-sm text-ink-hint">알림이 없습니다.</li>
              )}
              {(data?.alerts ?? []).map((a) => (
                <li key={a.id} className="border-b border-[var(--color-border)] px-4 py-3 last:border-0">
                  <p className="text-xs text-ink-hint">
                    {a.time} · {severityLabel(a.severity)}
                  </p>
                  <p className={`text-sm font-semibold ${scoreTextClass(a.score)}`}>
                    {scoreLabel(a.score)}
                  </p>
                  <p className="text-sm text-ink-muted">{a.message}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
        <div
          className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-white"
          aria-hidden
        >
          <User size={18} />
        </div>
      </div>
    </header>
  );
}
