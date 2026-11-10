import { scoreColorVar, scoreLabel } from "../lib/grade";
import { PSI_MAX, PSI_MIN } from "../lib/constants";

interface Props {
  score?: number | null;
  percent?: number | null;
  percentColor?: string;
  size?: number;
  stroke?: number;
}

export function ScoreRing({ score, percent, percentColor, size = 120, stroke = 12 }: Props) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const arc = c * 0.75;
  let frac = 0;
  let color = "var(--color-border)";
  let label = "--";
  if (percent != null) {
    frac = Math.max(0, Math.min(100, percent)) / 100;
    color = percentColor ?? "var(--color-good)";
    label = `${Math.round(percent)}%`;
  } else if (score != null) {
    frac = (PSI_MAX - Math.max(PSI_MIN, Math.min(PSI_MAX, score))) / (PSI_MAX - PSI_MIN);
    color = scoreColorVar(score);
    label = scoreLabel(score);
  }
  const filled = arc * frac;
  const cx = size / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
      <g transform={`rotate(225 ${cx} ${cx})`}>
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke="#E2E8F0"
          strokeWidth={stroke}
          strokeDasharray={`${arc} ${c}`}
          strokeLinecap="round"
        />
        <circle
          cx={cx}
          cy={cx}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeDasharray={`${filled} ${c}`}
          strokeLinecap="round"
        />
      </g>
      <text
        x={cx}
        y={cx + 5}
        textAnchor="middle"
        fontSize={size * 0.16}
        fontWeight={800}
        fill={score != null || percent != null ? color : "var(--color-text-hint)"}
      >
        {label}
      </text>
    </svg>
  );
}
