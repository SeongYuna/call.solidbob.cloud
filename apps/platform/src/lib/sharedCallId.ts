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
