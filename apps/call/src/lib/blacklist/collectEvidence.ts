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
 * C-6 갈래 → 근거 항목. `CallGuardFlag.category`가 백엔드 4종
 * (`insult`·`threat`·`sexual`·`distress`)으로 통일됐다(2026-09-15, 옛 한글 3종 걷어냄).
 *
 * `distress`는 `distress_count`로만 쌓인다 — `abuseTotal()`이 셋에서 뺀다.
 * 위기 신호는 화면 대응이 반대라(끊지 않고 연결) 폭언과 합산하지 않는다.
 */
const CATEGORY_TO_FIELD: Record<string, keyof BlacklistEvidence> = {
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
  // 아직 이 값을 실시간으로 세는 신호가 없다(호출부 어디도 옵션을 안 넘긴다) — "0건 확인됨"이
  // 아니라 "미측정"이다(`decisions/316`과 같은 원칙). `?? 0`으로 뭉개지 않는다.
  temperature_outliers: null,
};

export function collectEvidence(
  flags: CallGuardFlag[],
  options: { callDurationS?: number; temperatureOutliers?: number | null } = {},
): BlacklistEvidence {
  const evidence: BlacklistEvidence = {
    ...EMPTY_EVIDENCE,
    call_duration_s: options.callDurationS ?? 0,
    temperature_outliers: options.temperatureOutliers ?? null,
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
