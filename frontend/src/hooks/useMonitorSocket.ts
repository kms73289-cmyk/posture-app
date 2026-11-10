import { useEffect } from "react";
import { EMPTY_MONITOR } from "../types";
import { useMonitorStore } from "../store/monitorStore";

export function useMonitorSocket() {
  const setState = useMonitorStore((s) => s.setState);
  const setConnected = useMonitorStore((s) => s.setConnected);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;
    let retry = 0;
    let timer: number | undefined;

    const connect = () => {
      if (closed) return;
      const proto = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${location.host}/ws/state`);
      ws.onopen = () => {
        retry = 0;
        setConnected(true);
        ws?.send(JSON.stringify({ visible: document.visibilityState === "visible" }));
      };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          setState({ ...EMPTY_MONITOR, ...data, axes: { ...EMPTY_MONITOR.axes, ...data.axes } });
        } catch {
          /* ignore */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (closed) return;
        retry += 1;
        const delay = Math.min(8000, 400 * 2 ** retry);
        timer = window.setTimeout(connect, delay);
      };
      ws.onerror = () => ws?.close();
    };

    const onVis = () => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ visible: document.visibilityState === "visible" }));
      }
    };
    document.addEventListener("visibilitychange", onVis);
    connect();
    return () => {
      closed = true;
      document.removeEventListener("visibilitychange", onVis);
      if (timer) window.clearTimeout(timer);
      ws?.close();
    };
  }, [setConnected, setState]);
}
