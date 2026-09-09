import { getScenarioById } from "./scenarios";
import type { CallHistoryRow } from "./callHistory";
import type { MockScenario } from "./scenarios/types";

/**
 * 데모 통화 한 건의 해결 여부. 점수를 만들지 않는다.
 * F-2가 있으면 마지막 종결의 missing 이 비었는지.
 * 없으면 정보 안내형 — 상담기록에 마지막 발화가 있으면 해결.
 */
export function isDemoCallResolved(scenario: MockScenario): boolean {
  const last = scenario.closures[scenario.closures.length - 1];
  if (last !== undefined) {
    return last.event.missing.length === 0;
  }
  return scenario.transcripts.length > 0;
}

export function demoResolutionFlags(rows: readonly CallHistoryRow[]): boolean[] {
  return rows.map((row) => isDemoCallResolved(getScenarioById(row.scenarioId)));
}
