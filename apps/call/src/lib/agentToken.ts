/**
 * 상담원 전용 토큰(`_project/decisions/307`) 캡처.
 *
 * `POST /hub/blacklist-requests`가 이제 이 토큰을 요구한다 — 누가 요청했는지를
 * 더 이상 본문(`requested_by`)으로 안 믿고 토큰에서 가져온다. 관리자가
 * `POST /admin/agent-tokens`로 발급한 값을 상담원에게 링크로 건넨다.
 *
 * 화면에 입력창을 두지 않는다 — `apps/platform`의 `liveCallToken.ts`가 이미 쓰는
 * "URL 쿼리 한 번 → sessionStorage" 패턴과 같다. `?agent_token=` 로 한 번 방문하면
 * 이 탭에만 저장하고 쿼리는 그 자리에서 지운다.
 */
const STORAGE_KEY = "callguard:agentToken";
const QUERY_KEY = "agent_token";

export function captureAgentTokenFromUrl(): void {
  if (typeof window === "undefined") {
    return;
  }
  const url = new URL(window.location.href);
  const token = url.searchParams.get(QUERY_KEY);
  if (token === null || token.trim().length === 0) {
    return;
  }
  try {
    window.sessionStorage.setItem(STORAGE_KEY, token.trim());
  } catch {
    // 프라이빗 모드 등에서 저장이 막혀도 이번 방문에서는 어차피 못 쓴다 — 조용히 넘어간다
  }
  url.searchParams.delete(QUERY_KEY);
  window.history.replaceState({}, "", url.toString());
}

export function readAgentToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    return stored !== null && stored.length > 0 ? stored : null;
  } catch {
    return null;
  }
}
