/**
 * 상담원 전용 토큰(`_project/decisions/307`) 캡처.
 *
 * `POST /hub/blacklist-requests`가 이제 이 토큰을 요구한다 — 누가 요청했는지를
 * 더 이상 본문(`requested_by`)으로 안 믿고 토큰에서 가져온다. 관리자가
 * `POST /admin/agent-tokens`로 발급한 값을 상담원에게 링크로 건넨다.
 *
 * 화면에 입력창을 두지 않는다 — `?agent_token=` 로 한 번 방문하면 저장하고 쿼리는
 * 그 자리에서 지운다. **브라우저를 닫아도 남는다(localStorage)** — 관리자가 토큰을 한 번
 * 주면 그 상담원의 대기화면은 「로그아웃」을 누르거나 관리자가 폐기하기 전까지 다시
 * 열어도 로그인 화면 없이 바로 뜬다. 옛 판이 sessionStorage 에 남긴 토큰도 읽는다.
 */
const STORAGE_KEY = "callguard:agentToken";
const QUERY_KEY = "agent_token";

function save(token: string): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, token);
  } catch {
    // 프라이빗 모드 등에서 저장이 막혀도 이번 방문에서는 어차피 못 쓴다 — 조용히 넘어간다
  }
}

export function captureAgentTokenFromUrl(): void {
  if (typeof window === "undefined") {
    return;
  }
  const url = new URL(window.location.href);
  const token = url.searchParams.get(QUERY_KEY);
  if (token === null || token.trim().length === 0) {
    return;
  }
  save(token.trim());
  url.searchParams.delete(QUERY_KEY);
  window.history.replaceState({}, "", url.toString());
}

export function readAgentToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  for (const storage of [() => window.localStorage, () => window.sessionStorage]) {
    try {
      const stored = storage().getItem(STORAGE_KEY);
      if (stored !== null && stored.length > 0) {
        return stored;
      }
    } catch {
      // 이 저장소는 막혀 있다 — 다음 저장소를 본다
    }
  }
  return null;
}

/** 로그인 화면이 검증에 성공한 토큰을 저장한다 — URL 캡처와 같은 자리에 쓴다. */
export function writeAgentToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  save(token.trim());
}

/** 로그아웃 — 저장된 토큰을 지운다. 같은 브라우저의 다른 탭도 다음 확인 때 로그아웃된다. */
export function clearAgentToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  for (const storage of [() => window.localStorage, () => window.sessionStorage]) {
    try {
      storage().removeItem(STORAGE_KEY);
    } catch {
      // 지울 것도 없었던 셈이니 조용히 넘어간다
    }
  }
}
