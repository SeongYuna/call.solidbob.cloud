/**
 * A-5 mock — 영어 화자 · 대중교통 안내 (POLICY 4카테고리).
 * 상담원 발화는 TERM 2.1 · MANUAL 2.1 · TERM 1.2 · MANUAL 1.1 재사용.
 */
import type { MockScenario } from "./types";
import { agentTtsSent, cardBatch, utterance } from "./helpers";

const CALL_ID = "c_dasan_en_transit";
const DOMAIN = "dasan" as const;

const TERM_2_1 = {
  doc_id: "DASAN-TERM-2.1",
  title: "한별시 통합민원콜센터 민원안내지침 2.1",
} as const;

const MANUAL_2_1 = {
  doc_id: "DASAN-MANUAL-2.1",
  title: "한별시 통합민원콜센터 민원응대매뉴얼 2.1",
} as const;

export const transitEnScenario: MockScenario = {
  domain: DOMAIN,
  targetLanguage: "EN",
  transcripts: [
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e001",
      "customer",
      "Hi — I need to get from City Hall to the subway. Which bus should I take?",
      4100,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e002",
      "agent",
      "한별시 통합민원콜센터입니다. 버스·지하철 노선은 교통공사와 운수업체가 공개한 자료를 근거로 안내합니다.",
      8900,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e003",
      "customer",
      "How often do they run?",
      12400,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e004",
      "agent",
      "배차 간격은 변동될 수 있어서, 지금은 현재 기준임을 함께 말씀드립니다. 고정된 사실처럼 안내하지 않습니다.",
      17200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e005",
      "customer",
      "If I transfer, is there a discount?",
      20800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e006",
      "agent",
      "환승 할인 기준도 교통공사·운수업체 공개 자료를 근거로 안내합니다. 실시간 배차 정보는 변동될 수 있습니다.",
      25600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e007",
      "customer",
      "Can you promise I'll make the next train?",
      29100,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e008",
      "agent",
      "확정적으로 약속드리기는 어렵습니다. 센터는 일반적인 절차와 기준을 안내하는 창구이고, 최종은 소관 부서에 있습니다.",
      33800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e009",
      "customer",
      "So this is the current schedule, not a guarantee?",
      37200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_e010",
      "agent",
      "네. 배차처럼 변동 가능한 정보는 현재 기준임을 명시하고, 고정된 사실처럼 안내하지 않는 것이 응대 원칙입니다.",
      41800,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(CALL_ID, DOMAIN, 9400, [
      {
        title: "노선·환승 안내 원칙",
        summary:
          "버스·지하철 노선, 배차 간격, 환승 할인 기준은 교통공사·운수업체 공개 자료를 근거로 안내한다. 실시간 배차 정보는 변동될 수 있음을 함께 고지한다.",
        source: TERM_2_1,
        similarity_score: 0,
      },
      {
        title: "실시간성 있는 정보 안내",
        summary:
          "배차 간격처럼 변동 가능한 정보는 현재 기준임을 명시하고, 고정된 사실처럼 안내하지 않는다.",
        source: MANUAL_2_1,
        similarity_score: 0,
      },
    ]),
  ],
  wrapUp: {
    summary: [
      "영어로 버스·지하철 노선과 배차, 환승 할인을 문의했습니다.",
      "교통공사·운수업체 공개 자료 기준과 실시간 배차 변동, 확정 약속 금지를 안내했습니다.",
    ],
    category: "대중교통 안내",
    follow_ups: ["구체 노선 번호는 지식베이스에 없어 안내하지 않았습니다."],
  },
  translations: {
    seg_e001: {
      segment_id: 1,
      original_text:
        "Hi — I need to get from City Hall to the subway. Which bus should I take?",
      original_lang: "en",
      translated_text:
        "안녕하세요. 시청에서 지하철 타려면 어느 버스 타야 해요?",
    },
    seg_e003: {
      segment_id: 3,
      original_text: "How often do they run?",
      original_lang: "en",
      translated_text: "배차는 얼마나 자주 있나요?",
    },
    seg_e005: {
      segment_id: 5,
      original_text: "If I transfer, is there a discount?",
      original_lang: "en",
      translated_text: "환승하면 할인되나요?",
    },
    seg_e007: {
      segment_id: 7,
      original_text: "Can you promise I'll make the next train?",
      original_lang: "en",
      translated_text: "다음 열차 놓치지 않는다고 약속해 주실 수 있나요?",
    },
    seg_e009: {
      segment_id: 9,
      original_text: "So this is the current schedule, not a guarantee?",
      original_lang: "en",
      translated_text: "지금 기준 안내이지, 보장은 아니라는 거죠?",
    },
  },
  agentTts: agentTtsSent("en", [
    "seg_e002",
    "seg_e004",
    "seg_e006",
    "seg_e008",
    "seg_e010",
  ]),
  closures: [],
};
