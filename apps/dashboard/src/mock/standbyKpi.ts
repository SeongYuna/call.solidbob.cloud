/**
 * 대기화면 KPI·그래프. 측정값이 아니다. 화면만 채운다.
 */
export const MOCK_AGENT_NAME = "조서희";

export interface StandbyKpi {
  label: string;
  value: string;
  variant: "default" | "ok" | "warn";
}

export const MOCK_STANDBY_KPI: readonly StandbyKpi[] = [
  { label: "오늘 처리한 통화", value: "12건", variant: "default" },
  { label: "평균 처리 시간", value: "4분 20초", variant: "default" },
  { label: "컴플라이언스 경고", value: "2건", variant: "warn" },
  { label: "후속조치 미완료", value: "1건", variant: "default" },
];

export interface HourlyVolume {
  hour: string;
  count: number;
}

export const MOCK_HOURLY_VOLUME: readonly HourlyVolume[] = [
  { hour: "09", count: 2 },
  { hour: "10", count: 5 },
  { hour: "11", count: 8 },
  { hour: "12", count: 6 },
  { hour: "13", count: 9 },
  { hour: "14", count: 12 },
  { hour: "15", count: 7 },
  { hour: "16", count: 10 },
  { hour: "17", count: 4 },
  { hour: "18", count: 3 },
];
