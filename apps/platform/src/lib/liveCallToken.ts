/**
 * 공개 홍보 페이지(`apps/platform`)의 "통화 받기" 데모용 토큰 처리.
 *
 * 이 페이지는 누구나 보는 공개 사이트라, 토큰 입력창을 화면에 그냥 두지
 * 않는다 — `GATEWAY_INGEST_TOKEN`은 services/gateway README가 "진짜
 * 비밀"이라고 못박은 값이다. 대신 URL 쿼리(`?call_token=`)로 한 번 방문하면
 * 이 탭의 sessionStorage 에만 저장해 두고 쿼리는 그 자리에서 지운다 —
 * services/gateway의 `dev_page.ts`가 이미 쓰는 "탭에만 보관" 패턴과 같다.
 * 팀원에게는 이 쿼리가 붙은 링크를 따로 전달한다. 일반 방문자는 이 값이
 * 없어서 "통화 받기"를 눌러도 실제로 연결되지 않는다(2026-09-14 사용자 지시
 * — 테스트는 팀원만 해야 한다).
 */

const STORAGE_KEY = "callguard:ingestToken";
const QUERY_KEY = "call_token";

export function captureLiveCallTokenFromUrl(): void {
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

export function readLiveCallToken(): string | null {
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
