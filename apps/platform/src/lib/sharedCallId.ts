/**
 * 두 화면이 **같은 통화**로 붙게 하는 통화 ID — URL 쿼리 `?call_id=` 로만 받는다.
 *
 * 2026-09-17 왕복 테스트에서 드러난 결함: 홍보 페이지(고객 마이크)와 상담원 박스가 통화 ID 를 **각자** 만들어
 * (`test-web-platform-*` / `test-web-agent-*`) 콜 미디에이터가 두 통화로 갈랐다. 고객 발화가 상담원 화면에
 * 도착하지 않았고, 구독이 통화를 가리지 않아 서로의 1번 줄을 덮어썼다.
 * 두 화면을 같은 `?call_id=` 로 열면 한 통화가 된다.
 *
 * - 토큰(`call_token`)과 달리 **비밀이 아니다** — 저장하지 않고 URL 에서만 읽는다. 쿼리가 없으면 예전처럼 각자 만든다.
 *   sessionStorage 에 남기면 다음 통화까지 같은 ID 가 따라붙어 통화 둘이 한 기록으로 섞인다.
 * - 모양은 콜 미디에이터의 검사(`ws_server.ts` `CALL_ID`)와 같다. 안 맞으면 없는 것으로 본다 —
 *   미디에이터가 어차피 거절하고, DB 컬럼도 40자다.
 */
const QUERY_KEY = "call_id";
const CALL_ID = /^[A-Za-z0-9_.:-]{1,40}$/;

export function readSharedCallId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const value = new URL(window.location.href).searchParams.get(QUERY_KEY)?.trim() ?? "";
    return CALL_ID.test(value) ? value : null;
  } catch {
    return null;
  }
}

/** `CALL_ID` 정규식을 항상 만족하는 새 통화 ID — 영문·숫자만 쓰는 `Date.now().toString(36)`
 * 조합이라 별도 인코딩 없이 그대로 통과한다. */
function generateCallId(): string {
  return `call-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * 통화 ID가 URL에 없으면 새로 만들어 `?call_id=`로 반영하고, 있으면 그 값을 그대로 쓴다.
 * 두 화면(홍보 페이지·상담원 대시보드) 모두 이 함수를 거치면 어느 쪽이 먼저 열려도 같은
 * 통화 ID로 수렴한다 — 지금까지는 `readSharedCallId() ?? 각자 생성`이라 URL에 아무것도
 * 안 남아 상대 화면과 맞출 방법이 없었다(2026-09-22).
 *
 * `history.replaceState`를 쓴다 — 새 히스토리 엔트리를 쌓으면 "뒤로 가기"가 이 쿼리
 * 추가 자체를 되짚어야 해서 어색하다. URL을 못 바꾸는 환경(SSR 등)이어도 이번 통화는
 * 새로 만든 값으로 그대로 진행한다 — 상대와 안 맞을 뿐 통화 자체는 된다.
 */
export function ensureSharedCallId(): string {
  const existing = readSharedCallId();
  if (existing !== null) {
    return existing;
  }
  const generated = generateCallId();
  if (typeof window !== "undefined") {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set(QUERY_KEY, generated);
      window.history.replaceState({}, "", url.toString());
    } catch {
      // URL을 못 바꿔도 이번 통화는 이 값으로 진행한다 — 아래 return 은 그대로 유효하다
    }
  }
  return generated;
}
