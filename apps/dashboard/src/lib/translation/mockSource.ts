import type { TranslatedUtterance, AgentTtsStatus } from "../../types/contract";
import type { MockScenario } from "../../mock/scenarios/types";

/**
 * A-5 통번역 텍스트 소스. mock은 시나리오에 적어 둔 정적 번역이다.
 * 실시간 번역 API가 오면 mockGateway의 이 호출만 바꾸면 된다.
 */
export function mockCustomerTranslation(
  scenario: MockScenario,
  segmentId: string,
): TranslatedUtterance | undefined {
  return scenario.translations?.[segmentId];
}

export function mockAgentTts(
  scenario: MockScenario,
  segmentId: string,
): AgentTtsStatus | undefined {
  return scenario.agentTts?.[segmentId];
}
