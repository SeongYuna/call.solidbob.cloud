/**
 * C-6 mock — 재난지원금 지급 지연. 욕설·위협이 있어 콜가드와
 * 욕설 별표 마스킹과 콜가드 배너를 시연한다. 통화는 끊지 않는다 (decisions/201).
 */
import type { MockScenario } from "./types";
import { cardBatch, utterance } from "./helpers";

const CALL_ID = "c_dasan_009";
const DOMAIN = "dasan" as const;

const TERM_3_2 = {
  doc_id: "DASAN-TERM-3.2",
  title: "한별시 통합민원콜센터 민원안내지침 3.2",
} as const;

export const grantDelayKoScenario: MockScenario = {
  domain: DOMAIN,
  transcripts: [
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d001",
      "customer",
      "저기요, 제가 신청한 재난지원금이 왜 아직도 안 들어와요? 벌써 3주째예요.",
      500,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d002",
      "agent",
      "확인해 드리겠습니다. 신청하신 접수번호 알려주실 수 있을까요?",
      5000,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d003",
      "customer",
      "접수번호를 내가 왜 또 불러줘야 돼요? 지난번에도 다 말했잖아요! 진짜 미친 거 아니에요? 일을 어떻게 이따위로 해요?",
      12000,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d004",
      "agent",
      "불편을 드려 죄송합니다. 접수번호 확인이 안 되면 처리 상황을 조회할 방법이 없어서요.",
      20000,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d005",
      "customer",
      "됐고, 그쪽 이름 뭐예요? 확 민원 넣어버릴 거니까. 이렇게 사람 무시하고 일 처리 개판으로 하면 되는 거예요? 진짜 짜증나 죽겠네.",
      28000,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d006",
      "agent",
      "죄송합니다. 접수번호 확인 도와드릴 테니 잠시만 기다려 주시겠어요?",
      38000,
      null,
    ),
    utterance(
      CALL_ID,
      DOMAIN,
      "seg_d007",
      "customer",
      "야, 너 지금 나 갖고 노는 거지? 몇 번을 말해야 알아들어! 당장 처리 안 하면 가만 안 둘 거야.",
      45000,
      null,
    ),
  ],
  cardBatches: [
    cardBatch(CALL_ID, DOMAIN, 12000, [
      {
        title: "재난지원금 지급 조회",
        summary:
          "지급 지연 민원은 접수번호로 처리 상태를 확인한다. 상담원은 확정 지급일을 단정하지 않고, 폭언이 있어도 통화는 이어간다.",
        source: TERM_3_2,
        similarity_score: 0,
      },
    ]),
  ],
  wrapUp: {
    summary: [
      "재난지원금이 3주째 입금되지 않아 접수번호 확인을 요청했습니다.",
      "인신공격·모욕·위협 발화에 콜가드 경고와 음성 마스킹을 띄우고 통화는 이어갔습니다.",
    ],
    category: "고객 응대 · 콜가드 감지",
    follow_ups: ["접수번호 확인 후 지급 상태를 조회해 안내합니다."],
  },
  sentiment: {
    trajectory: ["불만", "격앙", "폭언", "위협"],
  },
  callGuard: {
    seg_d003: { segment_id: 3, category: "폭언", severity: "high" },
    seg_d005: { segment_id: 5, category: "욕설", severity: "high" },
    seg_d007: { segment_id: 7, category: "위협", severity: "high" },
  },
  closures: [],
};
