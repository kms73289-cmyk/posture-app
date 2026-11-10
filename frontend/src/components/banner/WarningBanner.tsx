import { useMonitorStore } from "../../store/monitorStore";

export function WarningBanner() {
  const banner = useMonitorStore((s) => s.state.banner);
  if (!banner.show) return null;
  const isDanger = banner.grade === 3;
  const bg = isDanger ? "#FC8181" : "#F6AD55";
  const bar = isDanger ? "#C53030" : "#C07820";
  const sub = isDanger ? "#FFD0D0" : "#FFF3D0";
  return (
    <div
      className="pointer-events-none fixed right-6 top-5 z-50 w-[370px] overflow-hidden rounded-xl text-white shadow-lg"
      role="alert"
      aria-live="assertive"
    >
      <div className="h-1" style={{ background: bar }} />
      <div className="px-4 py-3" style={{ background: bg }}>
        <p className="text-[15px] font-bold leading-snug">{banner.message}</p>
        <p className="mt-1 text-[13px]" style={{ color: sub }}>
          {banner.sub}
        </p>
      </div>
    </div>
  );
}
