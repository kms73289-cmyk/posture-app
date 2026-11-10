/** config.py fmt_duration / fmt_duration_ko */

export function fmtDurationKo(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  if (mins >= 60) return `${Math.floor(mins / 60)}시간 ${mins % 60}분`;
  return `${mins}분`;
}

export function fmtDurationCompact(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  if (mins >= 60) return `${Math.floor(mins / 60)}h${mins % 60}m`;
  return `${mins}m`;
}

export function fmtMmSs(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function sittingChip(seconds: number): string {
  if (seconds <= 0) return "오늘 착석 기록 없음";
  const mins = Math.floor(seconds / 60);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `오늘 ${h}시간 ${m}분 착석`;
}

export function formatDateKo(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${y}년 ${m}월 ${d}일`;
}
