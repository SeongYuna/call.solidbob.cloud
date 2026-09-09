/**
 * GET /hub/calls 목록 API 연결 전 임시 mock.
 * 자막 페이지 형태는 GET /hub/calls/{call_id}/transcript (`TranscriptPage`) 에 맞춘다.
 * inquiry_type 은 각 도메인 mock 시나리오 카드 title 을 그대로 쓴다.
 */
import { asteriskSpan } from "./scenarios/helpers";
import type {
  CallHistoryItem,
  Domain,
  MaskType,
  TranscriptPage,
  TranscriptQuerySegment,
} from "../types/contract";

interface HistoryRecord {
  item: CallHistoryItem;
  page: TranscriptPage;
}

function seg(
  id: number,
  speaker: TranscriptQuerySegment["speaker"],
  text: string,
  utterance_end_ms: number,
  maskType: MaskType | null = null,
): TranscriptQuerySegment {
  return {
    segment_id: id,
    speaker,
    text,
    masked:
      maskType === null ? [] : [{ type: maskType, span: asteriskSpan(text) }],
    is_final: true,
    utterance_end_ms,
  };
}

function page(
  callId: string,
  segments: TranscriptQuerySegment[],
): TranscriptPage {
  return {
    call_id: callId,
    segments,
    total: segments.length,
    limit: segments.length,
    offset: 0,
  };
}

function item(
  callId: string,
  started_at: string,
  domain: Domain,
  inquiry_type: string,
  hex: string,
): CallHistoryItem {
  return {
    call_id: callId,
    started_at,
    domain,
    inquiry_type,
    customer_ref: `고객 #${hex}`,
  };
}

const RECORDS: readonly HistoryRecord[] = [
  {
    item: item(
      "c_hist_fin_01",
      "2026-08-28T09:12:00+09:00",
      "finance",
      "분실·도난 신고",
      "a3f2",
    ),
    page: page("c_hist_fin_01", [
      seg(1, "customer", "안녕하세요. 카드를 잃어버려서 분실 신고하려고 전화드렸어요.", 4200),
      seg(2, "agent", "네 한별금융입니다. 본인 확인을 위해 카드번호 뒷자리 네 자리를 말씀해 주시겠어요?", 9100),
      seg(3, "customer", "카드번호는 **** 입니다", 12800, "P2"),
      seg(4, "agent", "접수했습니다. 지금 시점부터 해당 카드는 사용 정지됩니다. 신고 이전 부정사용액은 보상 기준에 따라 따로 안내드리겠습니다.", 17600),
    ]),
  },
  {
    item: item(
      "c_hist_fin_02",
      "2026-08-27T16:40:00+09:00",
      "finance",
      "부정사용 보상 기준",
      "7b1c",
    ),
    page: page("c_hist_fin_02", [
      seg(1, "customer", "신고하기 전에 쓰인 금액도 보상이 되나요?", 4100),
      seg(2, "agent", "신고 접수 이전 부정사용액은 보상 기준에 따라 따로 안내드립니다. 조사 전 보상을 확정적으로 안내하지 않습니다.", 8800),
      seg(3, "customer", "비밀번호를 다른 사람한테 말한 적은 없어요.", 12400),
      seg(4, "agent", "이용자 귀책 여부를 확인한 뒤에 보상 범위가 정해집니다. 비밀번호를 타인에게 알려준 경우 등에는 보상이 제한될 수 있습니다.", 17100),
    ]),
  },
  {
    item: item(
      "c_hist_fin_03",
      "2026-08-26T11:08:00+09:00",
      "finance",
      "중도해지수수료 산정",
      "c90e",
    ),
    page: page("c_hist_fin_03", [
      seg(1, "customer", "그때 같이 든 적금도 오늘 해지하면 수수료가 얼마나 나오는지도 궁금해요. 연락처 뒷자리는 **** 이에요.", 23100, "P4"),
      seg(2, "agent", "중도해지수수료는 약정금리와 중도해지 적용금리 차액에 비례해 산정됩니다. 예상 금액은 해지 신청 시점에 고지해야 하고, 고지 없이 해지를 종결할 수는 없습니다.", 28400),
      seg(3, "agent", "잔여 약정에 따라 우대금리 등 부가 혜택도 함께 소멸됩니다. 확인 되셨을까요?", 40800),
      seg(4, "customer", "네, 확인했습니다.", 44800),
    ]),
  },
  {
    item: item(
      "c_hist_fin_04",
      "2026-08-25T14:22:00+09:00",
      "finance",
      "재발급 절차",
      "2d44",
    ),
    page: page("c_hist_fin_04", [
      seg(1, "customer", "재발급도 바로 되나요? 분실 신고만 하면 새 카드가 오는 거죠?", 32100),
      seg(2, "agent", "재발급은 본인확인 절차를 거친 뒤 신청할 수 있습니다. 새 카드는 기존 번호와 다른 카드번호로 발급됩니다.", 36800),
      seg(3, "customer", "카드를 잃어버려서 분실 신고하려고 전화드렸어요.", 40100),
      seg(4, "agent", "분실·도난 신고 후 카드 재발급은 본인확인 절차를 거쳐 신청할 수 있습니다. 재발급 카드는 기존 카드와 별개의 카드번호로 발급됩니다.", 44200),
    ]),
  },
  {
    item: item(
      "c_hist_shop_01",
      "2026-08-28T10:05:00+09:00",
      "shopping",
      "반품 배송비 부담 기준",
      "8f1a",
    ),
    page: page("c_hist_shop_01", [
      seg(1, "customer", "어제 받은 옷이 사이즈가 안 맞아서 반품하려고요.", 4200),
      seg(2, "agent", "한별샵입니다. 단순 변심 반품은 왕복 배송비를 이용자가 부담합니다. 상품 하자·오배송이면 회사가 부담합니다.", 9100),
      seg(3, "customer", "그냥 안 맞아서요. 환불은 얼마가 되고 언제쯤 들어오나요?", 12800),
      seg(4, "agent", "반품 접수 시 환불 예정 금액과 소요 기간을 고지합니다. 상품 상태 확인이 끝나기 전에는 반품을 종결하지 않습니다.", 17600),
    ]),
  },
  {
    item: item(
      "c_hist_shop_02",
      "2026-08-27T13:18:00+09:00",
      "shopping",
      "반품 배송비 부담 기준",
      "b6e0",
    ),
    page: page("c_hist_shop_02", [
      seg(1, "customer", "상품 하자가 있어서 반품하면 배송비는 누가 내나요?", 4300),
      seg(2, "agent", "상품 하자·오배송의 경우 회사가 부담합니다. 단순 변심 반품의 왕복 배송비는 이용자가 부담합니다.", 8900),
      seg(3, "customer", "반품 신청할 때 그 기준을 말해 주시나요?", 12100),
      seg(4, "agent", "반품 신청 시 사유에 따른 배송비 부담 주체를 고지해야 합니다.", 15800),
    ]),
  },
  {
    item: item(
      "c_hist_shop_03",
      "2026-08-26T17:51:00+09:00",
      "shopping",
      "반품 배송비 부담 기준",
      "41aa",
    ),
    page: page("c_hist_shop_03", [
      seg(1, "customer", "어제 받은 옷이 사이즈가 안 맞아서 반품하려고요.", 4200),
      seg(2, "agent", "한별샵입니다. 단순 변심 반품은 왕복 배송비를 이용자가 부담합니다. 상품 하자·오배송이면 회사가 부담합니다.", 9100),
      seg(3, "customer", "그냥 안 맞아서요. 환불은 얼마가 되고 언제쯤 들어오나요?", 12800),
      seg(4, "agent", "반품 접수 시 환불 예정 금액과 소요 기간을 고지합니다. 상품 상태 확인이 끝나기 전에는 반품을 종결하지 않습니다.", 17600),
    ]),
  },
  {
    item: item(
      "c_hist_dasan_01",
      "2026-08-28T08:44:00+09:00",
      "dasan",
      "노선·환승 안내 원칙",
      "e3c7",
    ),
    page: page("c_hist_dasan_01", [
      seg(1, "customer", "2호선에서 버스로 갈아탈 때 환승 할인이 되나요?", 4200),
      seg(2, "agent", "한별시 통합민원콜센터입니다. 환승 할인 기준은 교통공사·운수업체 공개 자료를 근거로 안내합니다. 실시간 배차는 변동될 수 있습니다.", 9100),
      seg(3, "customer", "지금 오는 버스가 몇 분 남았는지도 알 수 있어요?", 12800),
      seg(4, "agent", "실시간 배차 정보는 변동될 수 있어 확정 시각을 안내하지 않습니다. 노선과 배차 간격은 공개 자료를 기준으로 말씀드립니다.", 17600),
    ]),
  },
  {
    item: item(
      "c_hist_dasan_02",
      "2026-08-27T19:03:00+09:00",
      "dasan",
      "노선·환승 안내 원칙",
      "09df",
    ),
    page: page("c_hist_dasan_02", [
      seg(1, "customer", "2호선에서 버스로 갈아탈 때 환승 할인이 되나요?", 4200),
      seg(2, "agent", "한별시 통합민원콜센터입니다. 환승 할인 기준은 교통공사·운수업체 공개 자료를 근거로 안내합니다. 실시간 배차는 변동될 수 있습니다.", 9100),
      seg(3, "customer", "지금 오는 버스가 몇 분 남았는지도 알 수 있어요?", 12800),
      seg(4, "agent", "실시간 배차 정보는 변동될 수 있어 확정 시각을 안내하지 않습니다. 노선과 배차 간격은 공개 자료를 기준으로 말씀드립니다.", 17600),
    ]),
  },
  {
    item: item(
      "c_hist_dasan_03",
      "2026-08-25T12:30:00+09:00",
      "dasan",
      "노선·환승 안내 원칙",
      "5a18",
    ),
    page: page("c_hist_dasan_03", [
      seg(1, "customer", "2호선에서 버스로 갈아탈 때 환승 할인이 되나요?", 4200),
      seg(2, "agent", "환승 할인 기준은 교통공사·운수업체 공개 자료를 근거로 안내합니다. 실시간 배차는 변동될 수 있습니다.", 8600),
      seg(3, "customer", "지금 오는 버스가 몇 분 남았는지도 알 수 있어요?", 12100),
      seg(4, "agent", "실시간 배차 정보는 변동될 수 있어 확정 시각을 안내하지 않습니다. 노선과 배차 간격은 공개 자료를 기준으로 말씀드립니다.", 16800),
    ]),
  },
  {
    item: item(
      "c_hist_hlt_01",
      "2026-08-28T11:27:00+09:00",
      "health",
      "증상 문의 응대 원칙",
      "d2b4",
    ),
    page: page("c_hist_hlt_01", [
      seg(1, "customer", "기침이 며칠째 안 나아요. 무슨 병일까요?", 4200),
      seg(2, "agent", "한별헬스콜입니다. 증상만으로 특정 질병이라고 단정하지 않습니다. 공식 자료 기준의 일반 정보만 안내합니다.", 9100),
      seg(3, "customer", "그래도 집에서 그냥 있어도 되나요?", 12800),
      seg(4, "agent", "지속되거나 악화되는 증상은 의료기관 방문을 권합니다. 진단·처방은 의료기관의 역할입니다.", 17600),
    ]),
  },
  {
    item: item(
      "c_hist_hlt_02",
      "2026-08-27T09:55:00+09:00",
      "health",
      "증상 문의 응대 원칙",
      "6c8f",
    ),
    page: page("c_hist_hlt_02", [
      seg(1, "customer", "기침이 며칠째 안 나아요. 무슨 병일까요?", 4200),
      seg(2, "agent", "한별헬스콜입니다. 증상만으로 특정 질병이라고 단정하지 않습니다. 공식 자료 기준의 일반 정보만 안내합니다.", 9100),
      seg(3, "customer", "그래도 집에서 그냥 있어도 되나요?", 12800),
      seg(4, "agent", "지속되거나 악화되는 증상은 의료기관 방문을 권합니다. 진단·처방은 의료기관의 역할입니다.", 17600),
    ]),
  },
  {
    item: item(
      "c_hist_hlt_03",
      "2026-08-26T15:14:00+09:00",
      "health",
      "증상 문의 응대 원칙",
      "77e1",
    ),
    page: page("c_hist_hlt_03", [
      seg(1, "customer", "기침이 며칠째 안 나아요. 무슨 병일까요?", 4200),
      seg(2, "agent", "한별헬스콜입니다. 증상만으로 특정 질병이라고 단정하지 않습니다. 공식 자료 기준의 일반 정보만 안내합니다.", 9100),
      seg(3, "customer", "그래도 집에서 그냥 있어도 되나요?", 12800),
      seg(4, "agent", "지속되거나 악화되는 증상은 의료기관 방문을 권합니다. 진단·처방은 의료기관의 역할입니다.", 17600),
    ]),
  },
];

/** GET /hub/calls 목록 API 연결 전 임시 mock */
export function listCallHistory(): CallHistoryItem[] {
  return [...RECORDS]
    .map((record) => record.item)
    .sort((a, b) => (a.started_at < b.started_at ? 1 : -1));
}

/** GET /hub/calls/{call_id}/transcript 연결 전 임시 mock */
export function getCallTranscript(callId: string): TranscriptPage | null {
  const found = RECORDS.find((record) => record.item.call_id === callId);
  return found === undefined ? null : found.page;
}
