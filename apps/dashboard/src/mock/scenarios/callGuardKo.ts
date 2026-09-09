/**
 * C-6 mock — 한국어 화자 · 생활하수도 시설 민원.
 * 상담원 발화는 TERM 3.2 · MANUAL 2.1 · 1.1 재사용.
 * 고객은 격앙된 말투만 쓰고, 자극적인 욕설·비하는 넣지 않는다.
 * 콜가드는 경고만 — 통화는 이어진다 (decisions/201).
 */
import type { MockScenario } from "./types";
import { cardBatch, utterance } from "./helpers";

const CALL_ID = "c_dasan_ko_callguard";
const DOMAIN = "dasan" as const;

const TERM_3_2 = {
  doc_id: "DASAN-TERM-3.2",
  title: "한별시 통합민원콜센터 민원안내지침 3.2",
} as const;

export const callGuardKoScenario: MockScenario = {
  domain: DOMAIN,
  transcripts: [
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g001",
      "customer",
      "배수관이 막혀서 집 앞에 물이 차요.",
      4200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g002",
      "agent",
      "한별시 통합민원콜센터입니다. 배수관 막힘 같은 시설 민원은 접수 후 현장 확인이 필요한 사안입니다.",
      9100,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g003",
      "customer",
      "오늘 안에 나와요? 지금 당장 와야죠.",
      12800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g004",
      "agent",
      "처리 예상 기간을 단정적으로 약속드리기는 어렵습니다. 시설 처리 기간처럼 변동 가능한 정보는 현재 기준임을 말씀드립니다.",
      17600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g005",
      "customer",
      "무슨 소리야! 답답하네 진짜.",
      21200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g006",
      "agent",
      "불편하신 점 이해합니다. 소관 부서 확인 후 안내드리겠습니다. 통화는 이어서 진행하겠습니다.",
      25800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g007",
      "customer",
      "지금 장난하세요?",
      29200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g008",
      "agent",
      "장난이 아닙니다. 접수 후 현장 확인이 필요한 사안이라, 확정 시각은 안내하지 않습니다.",
      33800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g009",
      "customer",
      "알겠어요. 접수만 해주세요.",
      37200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_g010",
      "agent",
      "접수하겠습니다. 현장 확인이 필요한 사안임을 다시 안내드립니다.",
      41800,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(CALL_ID, DOMAIN, 9600, [
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
      "배수관 막힘으로 현장 출동 시점을 물었습니다.",
      "처리 기간을 단정하지 않고 접수를 안내했습니다. 격앙된 발화에 콜가드 경고만 띄고 통화는 이어갔습니다.",
    ],
    category: "생활하수도 · 콜가드",
    follow_ups: ["현장 출동 시각은 지식베이스에 없어 안내하지 않았습니다."],
  },
  /** 발화 흐름: 문의 → 기간 재촉 → 격앙 → 수습. 점수는 없다. */
  sentiment: {
    trajectory: ["차분", "약간 격앙", "격앙", "차분"],
  },
  callGuard: {
    seg_g005: { segment_id: 5, category: "폭언", severity: "high" },
    seg_g007: { segment_id: 7, category: "폭언", severity: "low" },
  },
  closures: [],
};
