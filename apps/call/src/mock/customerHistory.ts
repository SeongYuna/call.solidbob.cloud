import type { MockScenarioId } from "./scenarios";

export interface CustomerHistoryEntry {
  /** 표시용 "MM-DD". 정렬은 안 한다 — 최근순으로 미리 적어 둔다. */
  date: string;
  inquiryType: string;
}

export interface CustomerHistorySummary {
  entries: CustomerHistoryEntry[];
  /** 지난 상담에서 상담원이 남긴 메모 요약 — 왜 다시 왔는지 짐작할 단서. */
  memo: string;
}

/**
 * 재상담 고객 이력 요약 — mock 전용.
 *
 * 서버에 F-3(반복 문의 연결)이 아직 없다 — 전화번호로 실제 과거 통화를 찾는
 * 기능이 없어서(customer_id는 스키마에만 있고 어떤 경로도 채우지 않는다),
 * "이 시나리오로 걸려오면 재상담 고객처럼 보인다"만 시나리오 ID에 고정해
 * 데모한다. 목록에 없는 시나리오는 첫 문의로 취급해 요약을 띄우지 않는다 —
 * 그래야 "누구나 재상담 고객"으로 보이는 거짓 인상을 주지 않는다(절대 원칙 2).
 */
const HISTORY: Partial<Record<MockScenarioId, CustomerHistorySummary>> = {
  "vi-deungbon": {
    entries: [
      { date: "09-01", inquiryType: "주민등록등본 재발급 절차" },
      { date: "08-15", inquiryType: "전입신고 서류 문의" },
    ],
    memo: "등본 재발급 절차를 안내했으나 인터넷 발급 방법을 다시 물어 재문의함",
  },
  "ko-masking": {
    entries: [{ date: "08-20", inquiryType: "민원 접수 본인확인" }],
    memo: "본인확인 서류를 준비하지 못해 재방문을 안내함",
  },
};

export function getCustomerHistory(
  scenarioId: MockScenarioId,
): CustomerHistorySummary | null {
  return HISTORY[scenarioId] ?? null;
}
