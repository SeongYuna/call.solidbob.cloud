/**
 * 상담원 대시보드의 "고객과 전화하기" 마이크 데모(AgentCallBox)용 토큰 처리.
 *
 * apps/platform 의 `liveCallToken.ts`와 같은 패턴이다 — `CALL_MEDIATOR_INGEST_TOKEN`은
 * services/call-mediator README가 "진짜 비밀"이라고 못박은 값이라 화면에 입력창을 두지
 * 않는다. URL 쿼리(`?call_token=`)로 한 번 방문하면 이 탭의 sessionStorage 에만
 * 저장하고 쿼리는 그 자리에서 지운다. 팀원에게는 이 쿼리가 붙은 링크를 따로
 * 전달한다 — 값이 없으면 "통화 시작"을 눌러도 실제로 연결되지 않는다
 * (2026-09-14 사용자 지시 — 테스트는 팀원만 해야 한다).
 */

const STORAGE_KEY = "callguard:ingestToken";
const QUERY_KEY = "call_token";

export function captureAgentCallTokenFromUrl(): void {
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

export function readAgentCallToken(): string | null {
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
