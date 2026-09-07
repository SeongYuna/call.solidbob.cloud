/**
 * 다산콜센터 mock — 일반행정 · 주민등록등본 재발급 (예시) + A-5 베트남어 화자.
 *
 * 상담원 발화는 knowledge-base/dasan/manual 3.1(대리 신청 시 위임장·대리인 신분증)을
 * 재사용한다. 고객 발화만 베트남어 원문+한글 번역 mock이다. 69종 구비서류 실측은
 * 지식베이스에 없다.
 */
import type { ClosureEvent } from "../../types/contract";
import { DASAN_DEUNGBON_RESOURCES } from "../localResources";
import type { MockScenario } from "./types";
import { agentTtsSent, cardBatch, utterance } from "./helpers";

const CALL_ID = "c_dasan_001";
const DOMAIN = "dasan" as const;
const SERVICE = "주민등록등본 재발급";

const DOCS_SOURCE = {
  doc_id: "DASAN-MANUAL-3.1",
  title: "한별시 통합민원콜센터 민원응대매뉴얼 3.1",
} as const;

function requiredDocsEvent(
  after: Pick<ClosureEvent, "evidence" | "missing" | "verdict" | "reason">,
): ClosureEvent {
  return {
    call_id: CALL_ID,
    // RequiredDocsType — 서비스명을 그대로 쓴다. ClosureType enum 이 아님.
    closure_type: SERVICE,
    ...after,
    source: DOCS_SOURCE,
    domain: DOMAIN,
    is_example: true,
  };
}

export const dasanScenario: MockScenario = {
  domain: DOMAIN,
  targetLanguage: "VI",
  transcripts: [
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d001",
      "customer",
      "Alo, xin chào. Tôi muốn xin lại bản sao hộ khẩu. Em tôi đi thay được không ạ?",
      4200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d002",
      "agent",
      "한별시 통합민원콜센터입니다. 본인이 가시면 신분증을 지참하시면 됩니다.",
      9100,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d003",
      "customer",
      "Thế em tôi đi thì sao ạ?",
      12800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d004",
      "agent",
      "대리 신청이면 위임장과 대리인 신분증이 필요합니다. 위임장 안내를 드리겠습니다.",
      17600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d005",
      "customer",
      "Vậy chỉ cần giấy ủy quyền với chứng minh thư của em là được chứ ạ?",
      21400,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d006",
      "agent",
      "네. 위임장, 대리인 신분증, 그리고 신청인 본인 확인용 신분증 사본을 함께 지참하시면 됩니다.",
      26200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d007",
      "customer",
      "Nhận luôn tại quầy được không ạ?",
      30100,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d008",
      "agent",
      "센터는 일반적인 절차와 기준을 안내하는 창구입니다. 개별 민원의 최종 처리는 소관 부서에 있어서, 제가 확정적으로 약속드리기는 어렵습니다.",
      34800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d009",
      "customer",
      "Nếu quá hạn cư trú thì sao ạ?",
      39200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d010",
      "agent",
      "불법체류이시면 창구에서 따로 확인이 필요합니다. 소관 부서 확인 후 안내드리겠습니다.",
      44000,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d011",
      "customer",
      "안내가 이렇게 늦으면 가만 안 둔다, 이거예요.",
      48800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d012",
      "agent",
      "불편을 드려 죄송합니다. 센터는 절차와 기준을 안내하는 창구입니다. 개별 민원의 최종 처리는 소관 부서에 있습니다.",
      53600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d013",
      "customer",
      "서류가 너무 많아서 너무 힘들어요. 어떻게 해야 할지 모르겠어요.",
      58200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d014",
      "agent",
      "본인 신청은 신분증, 대리 신청은 위임장과 대리인 신분증을 지참하시면 됩니다. 그 이상은 요구하지 않습니다.",
      62800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d015",
      "customer",
      "등본에 주민번호가 000000-0000000으로 나오나요?",
      67400,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d016",
      "agent",
      "주민등록번호 전체를 통화 중 구두로 요청하지 않습니다. 신분증을 지참하시면 창구에서 확인합니다.",
      72200,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(CALL_ID, DOMAIN, 9600, [
      {
        title: "주민등록등본 재발급 절차",
        summary:
          "본인 신청은 신분증을 지참한다. 대리 신청은 위임장과 대리인 신분증이 필요하며, 필요 여부를 빠짐없이 안내한다.",
        source: DOCS_SOURCE,
        similarity_score: 0,
      },
    ]),
  ],
  wrapUp: {
    summary: [
      "베트남어 화자가 주민등록등본 재발급에 필요한 서류를 문의했습니다.",
      "본인 신청은 신분증, 대리 신청은 위임장과 대리인 신분증을 빠짐없이 안내했습니다.",
      "창구 즉시 수령과 처리 확정은 센터 권한이 아니라 소관 부서 확인으로 안내했습니다.",
      "체류 기한 경과 문의에는 창구에서 따로 확인이 필요하다고 전했습니다.",
    ],
    category: "일반행정 · 등본 재발급",
    tags: ["주민등록등본 재발급", "행정 절차 안내"],
    follow_ups: [
      "관할 출입국관리사무소 안내 완료",
      "위임장 양식 발송",
      "재발급 처리 상태 콜백 예약",
    ],
    local_resources: [...DASAN_DEUNGBON_RESOURCES],
  },
  translations: {
    seg_d001: {
      segment_id: 1,
      original_text:
        "Alo, xin chào. Tôi muốn xin lại bản sao hộ khẩu. Em tôi đi thay được không ạ?",
      original_lang: "vi",
      translated_text:
        "안녕하세요. 등본을 다시 발급받으려면 뭐가 필요해요? 동생이 대신 가도 되나요?",
    },
    seg_d003: {
      segment_id: 3,
      original_text: "Thế em tôi đi thì sao ạ?",
      original_lang: "vi",
      translated_text: "동생이 대신 가면요?",
    },
    seg_d005: {
      segment_id: 5,
      original_text:
        "Vậy chỉ cần giấy ủy quyền với chứng minh thư của em là được chứ ạ?",
      original_lang: "vi",
      translated_text: "위임장이랑 동생 신분증만 있으면 되는 거죠?",
    },
    seg_d007: {
      segment_id: 7,
      original_text: "Nhận luôn tại quầy được không ạ?",
      original_lang: "vi",
      translated_text: "창구에서 바로 받을 수 있나요?",
    },
    seg_d009: {
      segment_id: 9,
      original_text: "Nếu quá hạn cư trú thì sao ạ?",
      original_lang: "vi",
      translated_text: "체류 기한이 지나면요?",
    },
  },
  agentTts: agentTtsSent("vi", [
    "seg_d002",
    "seg_d004",
    "seg_d006",
    "seg_d008",
    "seg_d010",
    "seg_d012",
    "seg_d014",
    "seg_d016",
  ]),
  closures: [
    {
      afterSegmentId: "seg_d002",
      event: requiredDocsEvent({
        reason: "서류 안내 진행 중",
        evidence: {
          신분증_사본: true,
          위임장: false,
          대리인_신분증: false,
        },
        verdict: "blocked",
        missing: ["위임장", "대리인_신분증"],
      }),
    },
    {
      afterSegmentId: "seg_d004",
      event: requiredDocsEvent({
        reason: "서류 안내 진행 중",
        evidence: {
          신분증_사본: true,
          위임장: true,
          대리인_신분증: false,
        },
        verdict: "blocked",
        missing: ["대리인_신분증"],
      }),
    },
    {
      afterSegmentId: "seg_d006",
      event: requiredDocsEvent({
        reason: "서류 안내 완료",
        evidence: {
          신분증_사본: true,
          위임장: true,
          대리인_신분증: true,
        },
        verdict: "approved",
        missing: [],
      }),
    },
  ],
};

/**
 * C-5 mock — 한국어 화자. 부록 A 후보 언어(vi·en·ja·zh·th)는 이미 썼다.
 * 절차는 MANUAL 1.2 민원 접수 최소 정보(성명·연락처·민원 대상 주소)와
 * 주민등록번호 전체 구두 요청 금지. 주소 변경 신고 같은 문서에 없는 절차는 쓰지 않는다.
 * 마스킹은 기존 utterance * 구간 + P1/P4/P7 (카드번호 P2 와 겹치지 않음).
 */
const MASK_CALL = "c_dasan_ko_masking";

const MANUAL_1_2 = {
  doc_id: "DASAN-MANUAL-1.2",
  title: "한별시 통합민원콜센터 민원응대매뉴얼 1.2",
} as const;

export const maskingKoScenario: MockScenario = {
  domain: DOMAIN,
  transcripts: [
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m001",
      "customer",
      "민원 접수하려면 뭘 불러야 해요?",
      4100,
      null,
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m002",
      "agent",
      "한별시 통합민원콜센터입니다. 민원 접수에 필요한 최소 정보는 성명, 연락처, 민원 대상 주소입니다. 그 이상은 요구하지 않습니다.",
      9200,
      null,
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m003",
      "customer",
      "주민번호 뒷자리는 *******이에요.",
      12800,
      "P1",
      "주민번호 뒷자리는 1234567이에요.",
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m004",
      "agent",
      "주민등록번호 전체를 통화 중 구두로 요청하지 않습니다. 뒷자리도 불러 주시지 않으셔도 됩니다.",
      17600,
      null,
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m005",
      "customer",
      "그럼 연락처는 *************입니다.",
      21200,
      "P4",
      "그럼 연락처는 010-2345-6789입니다.",
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m006",
      "agent",
      "연락처는 민원 접수에 필요한 최소 정보입니다. 그 이상은 받지 않습니다.",
      25600,
      null,
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m007",
      "customer",
      "민원 대상 주소는 ***********입니다.",
      29200,
      "P7",
      "민원 대상 주소는 서울 중구 다산로12입니다.",
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m008",
      "agent",
      "민원 대상 주소도 최소 정보에 해당합니다. 성명, 연락처, 주소 외의 개인정보는 요구하지 않습니다.",
      33800,
      null,
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m009",
      "customer",
      "주민번호 앞자리까지 전부 불러드릴까요?",
      37200,
      null,
    ),
    utterance(
      MASK_CALL,
      DOMAIN,
      "seg_m010",
      "agent",
      "불러 주시지 않으셔도 됩니다. 주민등록번호 전체를 구두로 요청하지 않는 것이 원칙입니다.",
      41800,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(MASK_CALL, DOMAIN, 9800, [
      {
        title: "불필요한 개인정보 요구 금지",
        summary:
          "민원 접수에 필요한 최소 정보(성명, 연락처, 민원 대상 주소 등) 이상을 요구하지 않는다. 주민등록번호 전체를 통화 중 구두로 요청하지 않는다.",
        source: MANUAL_1_2,
        similarity_score: 0,
      },
    ]),
  ],
  wrapUp: {
    summary: [
      "한국어로 민원 접수 시 확인할 개인정보를 문의했습니다.",
      "성명·연락처·주소만 최소 정보로 안내하고, 주민등록번호 전체 구두 요청 금지를 안내했습니다.",
    ],
    category: "일반행정 · 민원 접수 본인확인",
    follow_ups: ["접수 이후 소관 부서 처리는 지식베이스에 없어 안내하지 않았습니다."],
  },
  closures: [],
};
