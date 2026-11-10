/** config.py score_color / score_grade / score_label_ko 와 동일 분기. 색만 디자인 토큰. */

export function scoreLabel(psi: number | null | undefined): string {
  if (psi == null) return "부적정";
  if (psi <= 1) return "적정";
  if (psi <= 2) return "주의";
  return "부적정";
}

export function scoreLabelKo(psi: number | null | undefined): string {
  if (psi == null) psi = 3;
  if (psi <= 1) return "적정 자세";
  if (psi <= 2) return "주의 필요";
  return "부적정 자세";
}

export function scoreColorVar(psi: number | null | undefined): string {
  if (psi == null) return "var(--color-border)";
  if (psi <= 1) return "var(--color-good)";
  if (psi <= 2) return "var(--color-warn)";
  return "var(--color-danger)";
}

export function scoreTextClass(psi: number | null | undefined): string {
  if (psi == null) return "text-ink-hint";
  if (psi <= 1) return "text-good";
  if (psi <= 2) return "text-warn";
  return "text-danger";
}

export function badgeClass(psi: number | null | undefined): string {
  if (psi == null) return "bg-[#EDF2F7] text-ink-hint";
  if (psi <= 1) return "bg-[var(--badge-good-bg)] text-[var(--badge-good-fg)]";
  if (psi <= 2) return "bg-[var(--badge-warn-bg)] text-[var(--badge-warn-fg)]";
  return "bg-[var(--badge-danger-bg)] text-danger";
}

export const AXIS_LABEL: Record<string, string> = {
  neck: "목 굴곡",
  forward: "머리 앞돌출",
  lateral: "측방 기울기",
  shoulder: "어깨 기울기",
};

export function severityLabel(sev: string): string {
  if (sev === "warn") return "주의";
  if (sev === "danger") return "부적정";
  if (sev === "info") return "정보";
  return sev;
}
