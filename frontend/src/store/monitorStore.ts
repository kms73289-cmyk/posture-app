import { create } from "zustand";
import { EMPTY_MONITOR, type MonitorState } from "../types";

interface Toast {
  id: number;
  text: string;
  kind: "error" | "info";
}

interface MonitorStore {
  state: MonitorState;
  setState: (s: MonitorState) => void;
  connected: boolean;
  setConnected: (v: boolean) => void;
  toasts: Toast[];
  pushToast: (text: string, kind?: Toast["kind"]) => void;
  dismissToast: (id: number) => void;
  lastAlertAt: number;
  bumpAlert: () => void;
}

let toastSeq = 1;

export const useMonitorStore = create<MonitorStore>((set) => ({
  state: EMPTY_MONITOR,
  setState: (s) =>
    set((prev) => {
      const was = prev.state.banner.show;
      const now = s.banner.show;
      if (now && !was) {
        return { state: s, lastAlertAt: Date.now() };
      }
      return { state: s };
    }),
  connected: false,
  setConnected: (v) => set({ connected: v }),
  toasts: [],
  pushToast: (text, kind = "error") => {
    const id = toastSeq++;
    set((s) => ({ toasts: [...s.toasts, { id, text, kind }] }));
    window.setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, 8000);
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
  lastAlertAt: 0,
  bumpAlert: () => set({ lastAlertAt: Date.now() }),
}));
