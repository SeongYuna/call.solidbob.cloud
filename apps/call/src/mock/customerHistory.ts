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
 * ⚠ 2026-09-22 갱신 — 이전 주석("customer_id는 스키마에만 있고 어떤 경로도
 * 채우지 않는다")은 낡았다. `GET /hub/calls?customer_id=...`로 과거 통화
 * 이력을 조회하는 기능은 **이미 서버에 있다**(`call_list_router.py`) — 조건이
 * 맞으면(콜 미디에이터가 X-Caller-Phone을 넘기고 서버에 HMAC 키가 있으면)
 * `customer_id`도 실제로 채워진다.
 *
 * 그런데도 이 mock을 못 걷어내는 이유는 **막힌 지점이 하나 남아서다**:
 * 브라우저가 "지금 통화 중인 고객"의 `customer_id` 값을 알 방법이 없다.
 * `POST /hub/calls` 응답은 `customer_linked: bool`만 주고 실제 HMAC 값을
 * 안 준다 — 평문 전화번호가 브라우저에 닿지 않게 하려는 **의도된 설계**다.
 * `GET /hub/calls/{call_id}/record`·`.../transcript`, WS 이벤트 어디에도
 * `customer_id` 필드가 없다.
 *
 * 이 연결(서버가 현재 통화의 `customer_id`를 프론트에 알려줄 작은
 * 엔드포인트나 필드)이 생기면, 이 mock 카드를 `GET /hub/calls?customer_id=...`
 * 실 API로 교체할 수 있다. 그때까지는 "이 시나리오로 걸려오면 재상담 고객처럼
 * 보인다"만 시나리오 ID에 고정해 데모한다. 목록에 없는 시나리오는 첫 문의로
 * 취급해 요약을 띄우지 않는다 — 그래야 "누구나 재상담 고객"으로 보이는 거짓
 * 인상을 주지 않는다(절대 원칙 2).
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
