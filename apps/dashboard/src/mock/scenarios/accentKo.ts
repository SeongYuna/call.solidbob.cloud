/**
 * A-5 ⓑ mock — 어눌한 한국어. 번역이 아니다 (decisions/201).
 * 상담원 발화는 TERM 2.2 · 1.2 · MANUAL 1.1 · 1.2 · 1.4 재사용.
 * 등본·노선·하수도·감염병·처리기한·시설 민원과 겹치지 않는다.
 */
import type { MockScenario } from "./types";
import { cardBatch, utterance } from "./helpers";

const CALL_ID = "c_dasan_ko_accent";
const DOMAIN = "dasan" as const;

const TERM_2_2 = {
  doc_id: "DASAN-TERM-2.2",
  title: "한별시 통합민원콜센터 민원안내지침 2.2",
} as const;

export const accentKoScenario: MockScenario = {
  domain: DOMAIN,
  accentRecognition: true,
  transcripts: [
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a001",
      "customer",
      "안녕하세요... 저... 시어머니요. 다리... 잘 못 걸어요. 차 도움... 있어요?",
      6800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a002",
      "agent",
      "한별시 통합민원콜센터입니다. 교통약자 이동 지원 신청은 접수 방법과 필요 서류를 안내합니다.",
      12800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a003",
      "customer",
      "서류... 필요 있어요? 뭐... 가져가면 돼요?",
      18800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a004",
      "agent",
      "접수 방법과 필요 서류를 안내하고, 승인 여부는 소관 부서 심사 사항임을 안내합니다.",
      24800,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a005",
      "customer",
      "그러면... 오늘 바로... 돼요? 무조건... 돼요?",
      31200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a006",
      "agent",
      "무조건 처리된다고 말씀드리기는 어렵습니다. 소관 부서 확인 후 안내드리겠습니다.",
      37200,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a007",
      "customer",
      "아... 알겠어요. 어디로... 신청해요? 여기 전화... 돼요?",
      43600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a008",
      "agent",
      "센터는 일반적인 절차·기준을 안내하는 창구이며, 개별 민원의 최종 처리 권한은 소관 부서에 있습니다.",
      49600,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a009",
      "customer",
      "시어머니... 이름 말해도 돼요? 주민번호... 여기?",
      56000,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_a010",
      "agent",
      "민원 접수에 필요한 최소 정보 이상은 요구하지 않습니다. 주민등록번호 전체를 통화 중 구두로 요청하지 않습니다.",
      62000,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(CALL_ID, DOMAIN, 13600, [
      {
        title: "교통약자 이동 지원",
        summary:
          "교통약자(장애인·고령자·임산부) 이동 지원 신청 절차는 접수 방법과 필요 서류를 안내하고, 승인 여부는 소관 부서 심사 사항임을 명시한다.",
        source: TERM_2_2,
        similarity_score: 0,
      },
    ]),
  ],
  wrapUp: {
    summary: [
      "시어머니 보행이 어려워 교통약자 이동 지원을 물었습니다.",
      "접수·서류만 안내하고 승인은 소관 부서 심사라고 했습니다. 확정 약속과 주민번호 구두 요청은 하지 않았습니다.",
    ],
    category: "교통약자 이동 지원 · 억양",
    follow_ups: ["승인 여부는 소관 부서 심사라 센터에서 확정하지 않았습니다."],
  },
  closures: [],
};
