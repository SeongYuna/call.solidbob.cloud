/**
 * A-5 mock — 중국어 화자 · 코로나19 관련 상담 (POLICY 4카테고리).
 * 상담원 발화는 TERM 5.1 · 5.2 · MANUAL 4.1 · 1.3 · 1.4 재사용.
 * 격리 일수 등 문서에 없는 수치는 말하지 않는다.
 */
import type { MockScenario } from "./types";
import { agentTtsSent, cardBatch, utterance } from "./helpers";

const CALL_ID = "c_dasan_zh_covid";
const DOMAIN = "dasan" as const;

const TERM_5_1 = {
  doc_id: "DASAN-TERM-5.1",
  title: "한별시 통합민원콜센터 민원안내지침 5.1",
} as const;

const MANUAL_4_1 = {
  doc_id: "DASAN-MANUAL-4.1",
  title: "한별시 통합민원콜센터 민원응대매뉴얼 4.1",
} as const;

export const covidZhScenario: MockScenario = {
  domain: DOMAIN,
  targetLanguage: "ZH",
  transcripts: [
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z001",
      "customer",
      "您好，我有点发烧咳嗽，是不是新冠啊？",
      4200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z002",
      "agent",
      "한별시 통합민원콜센터입니다. 감염병 관련 문의는 질병관리본부·보건소 공식 지침을 인용해 안내합니다. 상담원이 개인적으로 진단하지는 않습니다.",
      9800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z003",
      "customer",
      "严重吗？应该没事吧？",
      13200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z004",
      "agent",
      "증상 문의에 괜찮을 거예요, 심각한 건 아닐 거예요 같은 안심 발언은 하지 않습니다. 공식 지침을 인용하고, 필요하면 의료기관·보건소 상담을 안내합니다.",
      18600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z005",
      "customer",
      "那要隔离几天？",
      22100,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z006",
      "agent",
      "감염병 대응 지침은 자주 갱신됩니다. 지식베이스에 반영된 최신 버전을 확인한 뒤 안내드리겠습니다. 근거를 찾지 못하면 확인 후 다시 안내드리겠습니다.",
      27800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z007",
      "customer",
      "那我该去哪儿问？",
      31200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z008",
      "agent",
      "의학적 진단이 필요한 문의는 의료기관이나 보건소 상담을 안내합니다.",
      35400,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z009",
      "customer",
      "你们现在讲的是最新规定吗？",
      38800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_z010",
      "agent",
      "안내 내용이 자주 바뀌는 주제라 색인된 최신 지침을 근거로 안내합니다. 오래된 지침으로 안내하지 않고, 근거를 찾지 못하면 확인 후 다시 안내드리겠습니다.",
      44200,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(CALL_ID, DOMAIN, 10300, [
      {
        title: "감염병 안내 원칙",
        summary:
          "감염병 관련 문의는 질병관리본부·보건소 공식 지침을 인용해 안내하고, 상담원의 개인적 의학 판단을 제공하지 않는다. 의학적 진단이 필요한 문의는 의료기관·보건소 상담을 안내한다.",
        source: TERM_5_1,
        similarity_score: 0,
      },
      {
        title: "의학적 판단 대신 공식 지침 인용",
        summary:
          "증상 문의에 상담원 개인 판단으로 안심 발언을 하지 않는다. 공식 지침을 인용하고, 필요 시 의료기관·보건소 상담을 안내한다.",
        source: MANUAL_4_1,
        similarity_score: 0,
      },
    ]),
  ],
  wrapUp: {
    summary: [
      "중국어로 발열·기침과 격리 기간을 문의했습니다.",
      "공식 지침 인용, 안심 발언 금지, 최신 지침 확인 후 안내, 의료기관·보건소 상담을 안내했습니다.",
    ],
    category: "코로나19 관련 상담",
    follow_ups: ["격리 일수는 지식베이스에 없어 수치를 말하지 않았습니다."],
  },
  translations: {
    seg_z001: {
      segment_id: 1,
      original_text: "您好，我有点发烧咳嗽，是不是新冠啊？",
      original_lang: "zh",
      translated_text: "안녕하세요. 열이 나고 기침이 나는데, 코로나인가요?",
    },
    seg_z003: {
      segment_id: 3,
      original_text: "严重吗？应该没事吧？",
      original_lang: "zh",
      translated_text: "심각한 거예요? 괜찮겠죠?",
    },
    seg_z005: {
      segment_id: 5,
      original_text: "那要隔离几天？",
      original_lang: "zh",
      translated_text: "그럼 며칠 격리해야 하나요?",
    },
    seg_z007: {
      segment_id: 7,
      original_text: "那我该去哪儿问？",
      original_lang: "zh",
      translated_text: "그럼 어디에 물어봐야 하나요?",
    },
    seg_z009: {
      segment_id: 9,
      original_text: "你们现在讲的是最新规定吗？",
      original_lang: "zh",
      translated_text: "지금 안내가 최신 규정인가요?",
    },
  },
  agentTts: agentTtsSent("zh", [
    "seg_z002",
    "seg_z004",
    "seg_z006",
    "seg_z008",
    "seg_z010",
  ]),
  closures: [],
};
