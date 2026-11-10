/** 매직 넘버 모음. 출처는 원본 파일. */

// ui/report.py · ui/history.py · ui/alerts.py 축 바 최대값
export const AXIS_MAX = {
  neck: 30,
  forward: 15,
  lateral: 20,
  shoulder: 12,
} as const;

export const AXIS_ROWS = [
  { key: "neck" as const, label: "목 굴곡", unit: "°", max: 30 },
  { key: "forward" as const, label: "머리 앞돌출", unit: "cm", max: 15 },
  { key: "lateral" as const, label: "측방 기울기", unit: "°", max: 20 },
  { key: "shoulder" as const, label: "어깨 기울기", unit: "°", max: 12 },
];

// analyzer.py _judge_axes (자세 분석 카드 눈금 참고용)
export const PSI_NECK_GOOD = 10;
export const PSI_NECK_WARN = 20;
export const PSI_LATERAL_GOOD = 10;
export const PSI_SHOULDER_GOOD = 10;
export const PSI_SHOULDER_WARN = 20;

// ui/dashboard.py 부적정 노출 게이지
export const BAD_PCT_GOOD = 20;
export const BAD_PCT_WARN = 50;

// config.py
export const PSI_MIN = 1;
export const PSI_MAX = 3;
export const NEUTRAL_NECK_KG = 5;

export const ALERT_INTERVALS: { value: number; label: string }[] = [
  { value: 10, label: "10초" },
  { value: 60, label: "1분" },
  { value: 600, label: "10분" },
  { value: 1800, label: "30분" },
  { value: 3600, label: "1시간" },
];

export const TIPS = [
  "허리를 곧게 펴고 어깨에 힘을 빼주세요!",
  "화면은 눈높이에 맞춰주세요",
  "50분마다 일어나 스트레칭하세요",
  "귀와 어깨가 일직선이 되도록 턱을 당겨주세요",
  "발바닥을 바닥에 붙이고 앉아주세요",
];

export const TIPS_BY_AXIS: Record<string, string> = {
  neck: "턱을 살짝 당기고 모니터를 눈높이에 맞춰 주세요.",
  forward: "머리를 뒤로 밀어 귀-어깨 정렬을 맞춰 주세요.",
  lateral: "양쪽 앉은뼈에 고르게 무게를 나눠 주세요.",
  shoulder: "어깨 힘을 빼고 양쪽 높이를 맞춰 주세요.",
};

export const ALERTS_PER_PAGE = 5;
