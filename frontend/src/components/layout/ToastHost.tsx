import { useMonitorStore } from "../../store/monitorStore";

export function ToastHost() {
  const toasts = useMonitorStore((s) => s.toasts);
  const dismissToast = useMonitorStore((s) => s.dismissToast);
  if (toasts.length === 0) return null;
  return (
    <div className="pointer-events-none absolute right-8 top-20 z-50 flex w-[min(420px,calc(100%-4rem))] flex-col gap-2">
      {toasts.map((t) => (
        <button
          key={t.id}
          type="button"
          className="pointer-events-auto rounded-xl bg-white px-4 py-3 text-left text-sm font-semibold text-danger shadow-card"
          onClick={() => dismissToast(t.id)}
        >
          {t.text}
        </button>
      ))}
    </div>
  );
}
