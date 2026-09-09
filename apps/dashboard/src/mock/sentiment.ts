import type { SentimentSummary } from "../types/contract";
import type { MockScenario } from "./scenarios/types";

const CALM = ["차분", "차분", "차분"];
const WITH_GUARD = ["차분", "격앙", "차분"];

/**
 * 감정분석 모델이 없어 시나리오에서 라벨만 만든다. 점수는 없다.
 * guard_flag_count 는 C-6 callGuard 키 수다 — 여기에 숫자를 적지 않는다.
 */
export function sentimentFromScenario(
  scenario: MockScenario,
  callId: string,
): SentimentSummary {
  const guard_flag_count = Object.keys(scenario.callGuard ?? {}).length;
  if (guard_flag_count > 0) {
    return {
      call_id: callId,
      trajectory: scenario.sentiment?.trajectory ?? WITH_GUARD,
      overall: "주의 필요",
      guard_flag_count,
    };
  }
  return {
    call_id: callId,
    trajectory: scenario.sentiment?.trajectory ?? CALM,
    overall: "양호",
    guard_flag_count: 0,
  };
}
