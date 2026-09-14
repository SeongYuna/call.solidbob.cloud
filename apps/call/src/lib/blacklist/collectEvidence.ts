/**
 * J-6 — 전환 요청에 실을 근거를 통화 상태에서 모은다.
 *
 * `_project/decisions/204`. **여기서 판정하지 않는다** — 세기만 한다.
 * 「이 고객은 악성이다」는 관리자가 정하고, 화면은 그 판단의 재료를 보여준다.
 */
import type {
  BlacklistEvidence,
  CallGuardFlag,
} from "../../types/contract";

/**
 * C-6 갈래 → 근거 항목. 프론트 임시 계약은 한글 3종(`폭언`·`욕설`·`위협`)이고
 * 백엔드는 4종(`insult`·`threat`·`sexual`·`distress`)이다.
 *
 * ⚠ **프론트에 `distress` 가 없다.** 위기 신호는 화면 대응이 반대라(끊지 않고 연결)
 * 그냥 매핑할 수 없다 — 계약을 맞출 때 정해야 한다([미결 항목](/open-items/)).
 * 지금은 백엔드 갈래가 들어오면 그대로 세고, 한글 3종은 아래 표로 옮긴다.
 */
const CATEGORY_TO_FIELD: Record<string, keyof BlacklistEvidence> = {
  욕설: "insult_count",
  폭언: "insult_count",
  위협: "threat_count",
  insult: "insult_count",
  threat: "threat_count",
  sexual: "sexual_count",
  distress: "distress_count",
};

export const EMPTY_EVIDENCE: BlacklistEvidence = {
  call_duration_s: 0,
  insult_count: 0,
  threat_count: 0,
  sexual_count: 0,
  distress_count: 0,
  temperature_outliers: 0,
};

export function collectEvidence(
  flags: CallGuardFlag[],
  options: { callDurationS?: number; temperatureOutliers?: number } = {},
): BlacklistEvidence {
  const evidence: BlacklistEvidence = {
    ...EMPTY_EVIDENCE,
    call_duration_s: options.callDurationS ?? 0,
    temperature_outliers: options.temperatureOutliers ?? 0,
  };
  for (const flag of flags) {
    const field = CATEGORY_TO_FIELD[flag.category];
    if (field) {
      evidence[field] += 1;
    }
  }
  return evidence;
}

/** 폭언 갈래 합계. **`distress` 를 넣지 않는다** — 사유가 아니다. */
export function abuseTotal(evidence: BlacklistEvidence): number {
  return evidence.insult_count + evidence.threat_count + evidence.sexual_count;
}

/**
 * 위기 신호가 섞였는가. 화면은 이때 **전문 기관 연결 안내를 대신 띄운다**
 * (DASAN-MANUAL-5.4). 요청 자체를 막지는 않는다 — 폭언과 위기가 한 통화에
 * 같이 있을 수 있고, 판단은 사람이 한다.
 */
export function hasDistress(evidence: BlacklistEvidence): boolean {
  return evidence.distress_count > 0;
}
