/**
 * A-5 mock — 태국어 화자 · 일반행정 문의 (등본 재발급이 아님).
 * 상담원 발화는 TERM 4.2(행정 처리 기한) · TERM 1.2 · MANUAL 1.1 · 1.4 재사용.
 */
import type { MockScenario } from "./types";
import { agentTtsSent, cardBatch, utterance } from "./helpers";

const CALL_ID = "c_dasan_th_admin";
const DOMAIN = "dasan" as const;

const TERM_4_2 = {
  doc_id: "DASAN-TERM-4.2",
  title: "한별시 통합민원콜센터 민원안내지침 4.2",
} as const;

const TERM_1_2 = {
  doc_id: "DASAN-TERM-1.2",
  title: "한별시 통합민원콜센터 민원안내지침 1.2",
} as const;

export const adminThScenario: MockScenario = {
  domain: DOMAIN,
  targetLanguage: "TH",
  transcripts: [
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t001",
      "customer",
      "สวัสดีค่ะ อยากทราบว่าเรื่องร้องเรียนใช้เวลานานแค่ไหน",
      4400,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t002",
      "agent",
      "한별시 통합민원콜센터입니다. 법정 처리기한이 있는 민원은 그 기한을 안내합니다.",
      9200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t003",
      "customer",
      "ต้องเสร็จภายในเวลานั้นเลยไหมคะ",
      12800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t004",
      "agent",
      "반드시 그 안에 끝난다처럼 절대 표현으로 안내하지는 않습니다.",
      17200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t005",
      "customer",
      "แล้วใครเป็นคนตัดสินใจคะ",
      20600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t006",
      "agent",
      "센터는 일반적인 절차와 기준을 안내하는 창구이며, 개별 민원의 최종 처리 권한은 소관 부서에 있습니다. 상담원이 소관 부서의 최종 결정을 확정적으로 대신 약속하지 않습니다.",
      26200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t007",
      "customer",
      "รับปากได้ไหมคะว่าต้องผ่าน",
      29600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t008",
      "agent",
      "무조건 처리된다고 말씀드리기는 어렵습니다. 소관 부서 확인 후 안내드리겠습니다.",
      34200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t009",
      "customer",
      "ถ้าเลยกำหนดแล้วจะเป็นยังไงคะ",
      37800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_t010",
      "agent",
      "소관 부서 확인이 필요한 사안이라, 확인 후 다시 안내드리겠습니다.",
      42200,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(CALL_ID, DOMAIN, 9700, [
      {
        title: "행정 처리 기한",
        summary:
          "법정 처리기한이 있는 민원은 그 기한을 안내하되, 반드시 그 안에 끝난다처럼 절대 표현으로 안내하지 않는다.",
        source: TERM_4_2,
        similarity_score: 0,
      },
      {
        title: "안내 범위의 한계",
        summary:
          "센터는 일반적인 절차·기준을 안내하는 창구이며, 개별 민원의 최종 처리 권한은 소관 부서에 있다. 상담원은 소관 부서의 최종 결정을 확정적으로 대신 약속하지 않는다.",
        source: TERM_1_2,
        similarity_score: 0,
      },
    ]),
  ],
  wrapUp: {
    summary: [
      "태국어로 민원 처리 기한을 문의했습니다.",
      "법정 기한 안내와 절대 표현 금지, 최종 처리는 소관 부서, 확정 약속 금지를 안내했습니다.",
    ],
    category: "일반행정 문의 · 처리 기한",
    follow_ups: ["구체 법정 일수는 지식베이스에 없어 숫자를 말하지 않았습니다."],
  },
  translations: {
    seg_t001: {
      segment_id: 1,
      original_text: "สวัสดีค่ะ อยากทราบว่าเรื่องร้องเรียนใช้เวลานานแค่ไหน",
      original_lang: "th",
      translated_text: "안녕하세요. 민원 넣으면 얼마나 걸려요?",
    },
    seg_t003: {
      segment_id: 3,
      original_text: "ต้องเสร็จภายในเวลานั้นเลยไหมคะ",
      original_lang: "th",
      translated_text: "그 기한 안에 꼭 끝나나요?",
    },
    seg_t005: {
      segment_id: 5,
      original_text: "แล้วใครเป็นคนตัดสินใจคะ",
      original_lang: "th",
      translated_text: "그럼 누가 결정하나요?",
    },
    seg_t007: {
      segment_id: 7,
      original_text: "รับปากได้ไหมคะว่าต้องผ่าน",
      original_lang: "th",
      translated_text: "통과된다고 약속해 주실 수 있나요?",
    },
    seg_t009: {
      segment_id: 9,
      original_text: "ถ้าเลยกำหนดแล้วจะเป็นยังไงคะ",
      original_lang: "th",
      translated_text: "기한이 지나면 어떻게 되나요?",
    },
  },
  agentTts: agentTtsSent("th", [
    "seg_t002",
    "seg_t004",
    "seg_t006",
    "seg_t008",
    "seg_t010",
  ]),
  closures: [],
};
