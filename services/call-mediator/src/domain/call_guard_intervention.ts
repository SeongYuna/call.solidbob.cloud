// Requirement: C-6
/**
 * C-6 베타 — 폭언 감지 뒤의 **대응 단계** 판정(`decisions/221`). 응대매뉴얼 5.1·5.2 를 옮긴 규칙이다(절대 원칙 9).
 *
 * - 1회 `warning` → 2회 `final_warning` → 3회 이상 `end_suggested`
 * - 1차 안내를 받은 뒤 `threat`·`sexual` 이면 곧바로 `end_suggested`(5.2)
 * - `distress` 는 넣지 않는다(5.4 — 종료가 아니라 전문 기관 연결)
 *
 * **시스템은 통화를 끊지 않는다**(5.2) — `end_suggested` 는 상담원에게 보이는 권고일 뿐이다.
 * 안내 문구는 고정 문안이다. 모델이 쓰지 않는다.
 */

export type InterventionStage = "warning" | "final_warning" | "end_suggested";

export interface Intervention {
  stage: InterventionStage;
  abuseCount: number;
  pauseMs: number;
  announcement: string | null;
  sourceDocId: string;
}

const ABUSE = new Set(["insult", "threat", "sexual"]);
const SEVERE = new Set(["threat", "sexual"]);

/** 안내 문구를 읽는 시간을 어림한 **예시값**이다 — 잰 값이 아니다(`decisions/141`). */
export const INTERVENTION_PAUSE_MS = 8000;

export const WARNING_ANNOUNCEMENT =
  "고객님, 원활한 상담을 위해 업무와 무관한 표현은 삼가 주시기 바랍니다. 이후에도 계속되면 상담이 종료될 수 있습니다. 잠시 후 상담을 이어가겠습니다.";
export const FINAL_WARNING_ANNOUNCEMENT =
  "다시 한 번 안내드립니다. 같은 표현이 계속되면 상담이 종료될 수 있습니다. 잠시 후 상담을 이어가겠습니다.";

export function categoriesOf(flags: readonly unknown[]): string[] {
  const out: string[] = [];
  for (const flag of flags) {
    if (typeof flag === "object" && flag !== null) {
      const category = (flag as Record<string, unknown>).category;
      if (typeof category === "string") out.push(category);
    }
  }
  return out;
}

export function nextIntervention(
  abuseCountBefore: number,
  categories: readonly string[],
): Intervention | null {
  const abuse = categories.filter((c) => ABUSE.has(c));
  if (abuse.length === 0) return null;
  const abuseCount = abuseCountBefore + 1;
  const severe = abuse.some((c) => SEVERE.has(c));
  if (abuseCount >= 3 || (abuseCount >= 2 && severe)) {
    return {
      stage: "end_suggested",
      abuseCount,
      pauseMs: 0,
      announcement: null,
      sourceDocId: "DASAN-MANUAL-5.2",
    };
  }
  if (abuseCount === 2) {
    return {
      stage: "final_warning",
      abuseCount,
      pauseMs: INTERVENTION_PAUSE_MS,
      announcement: FINAL_WARNING_ANNOUNCEMENT,
      sourceDocId: "DASAN-MANUAL-5.1",
    };
  }
  return {
    stage: "warning",
    abuseCount,
    pauseMs: INTERVENTION_PAUSE_MS,
    announcement: WARNING_ANNOUNCEMENT,
    sourceDocId: "DASAN-MANUAL-5.1",
  };
}
