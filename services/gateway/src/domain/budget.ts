// Requirement: COST-1
/**
 * STT 사용량 2차 가드의 규칙 — 순수 계산만 한다(파일·시계는 모른다).
 *
 * 장부 형식은 `scripts/transcribe_batch.py` 의 `Budget` 과 **같다** — `{"YYYY-MM-DD": 초}`.
 * 같은 머신에서 배치 전사와 게이트웨이가 한 장부를 나눠 써야 캡이 두 배가 되지 않는다
 * ([미결] 2026-09-03 A-1 게이트웨이 자리 항목).
 *
 * 배치 스크립트와 다른 점 하나 — **캡이 비어 있으면 연다가 아니라 막는다(fail-closed).**
 * 배치는 요청 전에 길이를 알지만 스트림은 끝을 모른다. 캡 없이 열린 스트림은 누가 끊기
 * 전까지 계속 과금된다.
 */

export type Ledger = Record<string, number>;

export interface Caps {
  perDay: number;
  perMonth: number;
}

export type OpenDecision = { ok: true; remainingSeconds: number } | { ok: false; reason: string };

/** 스트림을 새로 열려면 남아 있어야 하는 최소 초. 1초 미만으로 열면 열자마자 끊긴다. */
export const MIN_SECONDS_TO_OPEN = 1;

export function usedOnDay(ledger: Ledger, day: string): number {
  return ledger[day] ?? 0;
}

export function usedInMonth(ledger: Ledger, month: string): number {
  let total = 0;
  for (const [key, seconds] of Object.entries(ledger)) {
    if (key.startsWith(month)) {
      total += seconds;
    }
  }
  return total;
}

export function capsConfigured(caps: Caps): boolean {
  return caps.perDay > 0 && caps.perMonth > 0;
}

/** 일·월 한도 중 더 빡빡한 쪽의 남은 초. 음수는 0 으로 자른다. */
export function remainingSeconds(ledger: Ledger, caps: Caps, day: string): number {
  const dayLeft = caps.perDay - usedOnDay(ledger, day);
  const monthLeft = caps.perMonth - usedInMonth(ledger, day.slice(0, 7));
  return Math.max(0, Math.min(dayLeft, monthLeft));
}

export function decideOpen(ledger: Ledger, caps: Caps, day: string): OpenDecision {
  if (!capsConfigured(caps)) {
    return {
      ok: false,
      reason: "STT_MAX_SECONDS_PER_DAY·_MONTH 가 비어 있다 — 캡 없이는 스트림을 열지 않는다(COST-1)",
    };
  }
  const usedDay = usedOnDay(ledger, day);
  if (usedDay + MIN_SECONDS_TO_OPEN > caps.perDay) {
    return { ok: false, reason: `STT 일 한도 초과 (${usedDay.toFixed(0)}/${caps.perDay}초)` };
  }
  const usedMonth = usedInMonth(ledger, day.slice(0, 7));
  if (usedMonth + MIN_SECONDS_TO_OPEN > caps.perMonth) {
    return { ok: false, reason: `STT 월 한도 초과 (${usedMonth.toFixed(0)}/${caps.perMonth}초)` };
  }
  return { ok: true, remainingSeconds: remainingSeconds(ledger, caps, day) };
}

export function charged(ledger: Ledger, day: string, seconds: number): Ledger {
  return { ...ledger, [day]: usedOnDay(ledger, day) + seconds };
}

/** 로컬 시각 기준 `YYYY-MM-DD` — 파이썬 `dt.date.today()` 와 같은 날짜를 가리켜야 한다. */
export function localDay(now: Date): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** PCM16 모노 바이트 수 → 초. 과금 단위가 오디오 길이라 벽시계가 아니라 이것으로 센다. */
export function pcm16Seconds(byteLength: number, sampleRate: number): number {
  return byteLength / (sampleRate * 2);
}
