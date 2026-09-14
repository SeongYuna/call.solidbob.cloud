/**
 * A-5 mock — 일본어 화자 · 생활하수도 관련 문의 (POLICY 4카테고리).
 * 상담원 발화는 TERM 3.1 · 3.2 · MANUAL 2.1 · TERM 1.2 · MANUAL 1.1 재사용.
 */
import type { MockScenario } from "./types";
import { agentTtsSent, cardBatch, utterance } from "./helpers";

const CALL_ID = "c_dasan_ja_sewer";
const DOMAIN = "dasan" as const;

const TERM_3_1 = {
  doc_id: "DASAN-TERM-3.1",
  title: "한별시 통합민원콜센터 민원안내지침 3.1",
} as const;

const TERM_3_2 = {
  doc_id: "DASAN-TERM-3.2",
  title: "한별시 통합민원콜센터 민원안내지침 3.2",
} as const;

export const sewerJaScenario: MockScenario = {
  domain: DOMAIN,
  targetLanguage: "JA",
  transcripts: [
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j001",
      "customer",
      "すみません、下水道の料金はどうやって決まるんですか。",
      4300,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j002",
      "agent",
      "한별시 통합민원콜센터입니다. 하수도 사용료는 사용량에 연동해 산정합니다.",
      9100,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j003",
      "customer",
      "うちの請求額、今すぐ分かりますか。",
      12600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j004",
      "agent",
      "개별 세대의 정확한 청구액은 상하수도 사업본부 조회가 필요합니다. 여기서 금액을 확정해 드리지는 않습니다.",
      17800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j005",
      "customer",
      "排水管が詰まってるみたいなんです。",
      21400,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j006",
      "agent",
      "배수관 막힘 같은 시설 민원은 접수 후 현장 확인이 필요한 사안입니다.",
      25800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j007",
      "customer",
      "今日中に直りますか。",
      29200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j008",
      "agent",
      "처리 예상 기간을 단정적으로 약속드리기는 어렵습니다. 시설 처리 기간처럼 변동 가능한 정보는 현재 기준임을 명시하는 것이 원칙입니다.",
      34400,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j009",
      "customer",
      "現場確認には必ず来てもらえるんですか。",
      37900,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_j010",
      "agent",
      "센터는 일반적인 절차를 안내하는 창구입니다. 소관 부서 확인 후 안내드리겠습니다.",
      42400,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(CALL_ID, DOMAIN, 9600, [
      {
        title: "하수도 요금 및 사용료",
        summary:
          "하수도 사용료 산정 기준(사용량 연동)을 안내하며, 개별 세대의 정확한 청구액은 상하수도 사업본부 조회가 필요함을 안내한다.",
        source: TERM_3_1,
        similarity_score: 0,
      },
      {
        title: "시설 고장·민원 접수",
        summary:
          "배수관 막힘, 맨홀 고장 등 시설 민원은 접수 후 현장 확인이 필요한 사안임을 안내하고, 처리 예상 기간을 단정적으로 약속하지 않는다.",
        source: TERM_3_2,
        similarity_score: 0,
      },
    ]),
  ],
  wrapUp: {
    summary: [
      "일본어로 하수도 사용료와 배수관 막힘을 문의했습니다.",
      "사용량 연동 산정, 청구액은 본부 조회, 시설 민원은 현장 확인·기간 단정 금지를 안내했습니다.",
    ],
    category: "생활하수도 관련 문의",
    follow_ups: ["현장 출동 시각은 지식베이스에 없어 안내하지 않았습니다."],
  },
  translations: {
    seg_j001: {
      segment_id: 1,
      original_text: "すみません、下水道の料金はどうやって決まるんですか。",
      original_lang: "ja",
      translated_text: "죄송한데, 하수도 요금은 어떻게 정해지나요?",
    },
    seg_j003: {
      segment_id: 3,
      original_text: "うちの請求額、今すぐ分かりますか。",
      original_lang: "ja",
      translated_text: "우리 집 청구액, 지금 바로 알 수 있나요?",
    },
    seg_j005: {
      segment_id: 5,
      original_text: "排水管が詰まってるみたいなんです。",
      original_lang: "ja",
      translated_text: "배수관이 막힌 것 같아요.",
    },
    seg_j007: {
      segment_id: 7,
      original_text: "今日中に直りますか。",
      original_lang: "ja",
      translated_text: "오늘 안에 고쳐지나요?",
    },
    seg_j009: {
      segment_id: 9,
      original_text: "現場確認には必ず来てもらえるんですか。",
      original_lang: "ja",
      translated_text: "현장 확인은 꼭 나와 주시나요?",
    },
  },
  agentTts: agentTtsSent("ja", [
    "seg_j002",
    "seg_j004",
    "seg_j006",
    "seg_j008",
    "seg_j010",
  ]),
  closures: [],
};
