import { NavLink } from "react-router-dom";
import { Camera, BarChart3, CalendarDays, Settings } from "lucide-react";
import logoMark from "../../assets/logo-mark.svg";
import { useMonitorStore } from "../../store/monitorStore";

const NAV = [
  { to: "/", label: "자세 측정", icon: Camera, end: true },
  { to: "/report", label: "자세 분석", icon: BarChart3, end: false },
  { to: "/history", label: "기록", icon: CalendarDays, end: false },
  { to: "/settings", label: "설정", icon: Settings, end: false },
];

export function Sidebar() {
  const st = useMonitorStore((s) => s.state);
  let status = "오프라인";
  let dot = "bg-ink-hint";
  if (st.running && !st.cameraOk) {
    status = "카메라 연결 중";
    dot = "bg-warn";
  } else if (st.running && st.modelLoading) {
    status = "AI 모델 로딩 중";
    dot = "bg-warn";
  } else if (st.running && !st.calibrated) {
    status = "기준 설정 중";
    dot = "bg-warn";
  } else if (st.running) {
    status = "측정 중";
    dot = "bg-good";
  }

  return (
    <aside className="flex w-[240px] shrink-0 flex-col bg-white">
      <div className="flex items-center gap-2.5 px-5 pb-3 pt-6" aria-label="바른자세">
        <img src={logoMark} alt="" className="h-9 w-9 shrink-0" />
        <span className="text-[20px] font-extrabold tracking-tight text-ink">바른자세</span>
      </div>
      <nav className="mt-2 flex-1 space-y-1 px-3">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-[14px] transition ${
                isActive
                  ? "bg-[var(--nav-active-bg)] font-semibold text-primary"
                  : "text-ink-muted hover:bg-[#F7F8FA]"
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={`h-5 w-[3px] rounded-full ${isActive ? "bg-primary" : "bg-transparent"}`}
                />
                <item.icon size={18} strokeWidth={isActive ? 2.4 : 2} />
                {item.label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-3">
        <div className="flex items-center gap-2 text-[13px] text-ink-muted">
          <span className={`inline-block h-2 w-2 rounded-full ${dot}`} />
          {status}
        </div>
      </div>
      <div className="m-4 mt-0 rounded-2xl bg-[linear-gradient(180deg,#F3FBF7,#EAF6FF)] p-4">
        <p className="text-[13px] font-bold text-primary">오늘도 바른 자세로!</p>
        <SitSvg />
      </div>
    </aside>
  );
}

function SitSvg() {
  return (
    <svg viewBox="0 0 120 72" className="mt-2 h-16 w-full" aria-hidden>
      <ellipse cx="78" cy="62" rx="28" ry="5" fill="#D1FAE5" />
      <path d="M40 58 V22" stroke="#0DA573" strokeWidth="3" strokeLinecap="round" />
      <circle cx="40" cy="16" r="7" fill="#0DA573" />
      <path d="M40 28 C52 30 58 42 56 52" stroke="#34D399" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path d="M40 32 C28 36 24 44 28 54" stroke="#34D399" strokeWidth="3" fill="none" strokeLinecap="round" />
      <path d="M56 52 H78" stroke="#A0AEC0" strokeWidth="3" strokeLinecap="round" />
      <path d="M70 52 V62 H90 V44 H78" stroke="#CBD5E0" strokeWidth="3" fill="none" strokeLinejoin="round" />
      <path d="M18 50 C22 40 30 38 34 46" fill="#86EFAC" opacity=".8" />
    </svg>
  );
}
