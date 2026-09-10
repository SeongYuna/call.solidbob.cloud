/**
 * J-6 근거 읽기용 헬퍼. `apps/dashboard`의 `lib/blacklist/collectEvidence.ts`와
 * 달리 근거를 **모으지 않는다** — 관리자는 이미 만들어진 `BlacklistEvidence`를
 * 읽기만 하므로 `collectEvidence()`(콜가드 플래그 집계)는 여기 없다.
 */
import type { BlacklistEvidence } from "../../types/blacklist";

/** 폭언 갈래 합계. **`distress`를 넣지 않는다** — 사유가 아니다. */
export function abuseTotal(evidence: BlacklistEvidence): number {
  return evidence.insult_count + evidence.threat_count + evidence.sexual_count;
}

/**
 * 위기 신호가 섞였는가. 화면은 이때 **전문 기관 연결 안내를 대신 띄운다**
 * (DASAN-MANUAL-5.4). 요청 자체를 막지는 않는다.
 */
export function hasDistress(evidence: BlacklistEvidence): boolean {
  return evidence.distress_count > 0;
}
