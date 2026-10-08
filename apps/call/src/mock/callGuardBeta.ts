// Requirement: C-6
/**
 * C-6 베타 mock 스위치 — 주소창 `?c6beta=1`. 미디에이터의 `CALL_GUARD_INTERVENTION_BETA=1` 과 같은 자리다.
 * 꺼져 있으면 mock 재생은 지금과 똑같다(티켓 `w8-c6-intervention-overlay-ui` — 메시지가 안 와도 화면이 같아야 한다).
 */
export function isCallGuardBetaPreview(search: string = window.location.search): boolean {
  return new URLSearchParams(search).get("c6beta") === "1";
}
