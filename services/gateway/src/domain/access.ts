// Requirement: SEC-1, COST-1
/**
 * 게이트웨이 접속 허용 규칙 — `/ws`(자막을 받는다)·`/ingest`(STT 과금을 쓴다) 둘 다에 건다.
 *
 * - **믿는 주소(기본: 루프백)** 는 토큰 없이 받는다. 로컬 개발이 설정 없이 돈다. 쿠버네티스에서는
 *   Traefik 을 거쳐 들어오므로 루프백이 아니다 — `kubectl port-forward` 처럼 파드 안으로 직접 들어온
 *   것만 루프백이고, 그건 클러스터 권한이 있는 사람이다.
 * - 그 밖은 **토큰이 맞아야** 받는다. 토큰이 설정돼 있지 않으면 **전부 거절한다(fail-closed)** —
 *   배포하면서 토큰을 빼먹으면 «아무나 받는다» 가 아니라 «아무도 못 붙는다» 로 드러난다.
 *
 * **토큰은 문마다 따로다** (a5 세션 검토, 2026-09-11) —
 * - `/ingest` = `GATEWAY_INGEST_TOKEN`. STT 과금을 쓰는 문이라 **진짜 비밀**이다. 생산자(서버 쪽 스크립트)만
 *   갖고, `Authorization` 헤더로만 받는다 — URL 에 실리면 접근 로그·기록에 남는다.
 * - `/ws` = `GATEWAY_VIEW_TOKEN`. 대시보드는 공개 사이트라 브라우저가 내는 토큰은 번들에서 누구나 읽는다.
 *   **비밀이 아니고 무작위 스캔만 막는다.** 둘을 가른 이유가 이것이다 — 하나였다면 번들에서 뽑은 값으로
 *   과금 문까지 열렸다.
 *
 * ⚠ `/ws` 를 제대로 막으려면 **사람별 인증**(상담원 로그인)이 있어야 한다. 서버에도 없다 — 미결 항목
 * 「서버에 인증이 없다」가 풀릴 때 같이 옮긴다. 이 토큰이 그것을 대신한다고 적지 않는다.
 */
import { createHash, timingSafeEqual } from "node:crypto";

export type AccessDecision = { ok: true } | { ok: false; reason: string };

export function isLoopback(address: string | undefined): boolean {
  if (address === undefined) {
    return false;
  }
  const bare = address.startsWith("::ffff:") ? address.slice("::ffff:".length) : address;
  return bare === "::1" || bare.startsWith("127.");
}

/**
 * @param expected  설정된 토큰. 빈 문자열이면 설정되지 않은 것
 * @param presented 요청이 내민 토큰. 없으면 null
 * @param trusted   요청 주소가 믿는 주소(루프백)인가
 */
export function decideAccess(expected: string, presented: string | null, trusted: boolean): AccessDecision {
  if (trusted) {
    return { ok: true };
  }
  if (expected.length === 0) {
    return { ok: false, reason: "이 문의 토큰이 설정되지 않아 이 머신 밖 접속은 받지 않는다" };
  }
  if (presented === null || presented.length === 0) {
    return { ok: false, reason: "토큰이 없다" };
  }
  if (!sameSecret(expected, presented)) {
    return { ok: false, reason: "토큰이 맞지 않다" };
  }
  return { ok: true };
}

/** 길이가 달라도 걸리는 시간이 같게 — 해시로 길이를 맞춘 뒤 상수 시간 비교. */
function sameSecret(a: string, b: string): boolean {
  const left = createHash("sha256").update(a).digest();
  const right = createHash("sha256").update(b).digest();
  return timingSafeEqual(left, right);
}

/**
 * 요청이 프록시를 거쳐 왔는가. **소켓이 루프백이어도 프록시 헤더가 있으면 믿지 않는다** —
 * ngrok 같은 터널은 인터넷에서 온 요청을 로컬에서 다시 열어 루프백으로 넘긴다. 이걸 안 보면
 * `ngrok http 8080` 한 줄로 문이 통째로 열린다(2026-09-11, `decisions/109`).
 * 헤더로 신뢰를 **주지는** 않는다 — 빼앗기만 한다. 헤더를 꾸며 붙인 쪽은 스스로 문을 닫을 뿐이다.
 */
export function forwardedByProxy(headers: Record<string, string | string[] | undefined>): boolean {
  return ["x-forwarded-for", "forwarded", "x-real-ip"].some((name) => headers[name] !== undefined);
}

/**
 * 브라우저 WebSocket 은 헤더를 못 붙인다 — 대신 서브프로토콜 목록은 보낼 수 있다
 * (`new WebSocket(url, ["callguard", "bearer.<토큰>"])`). URL 에 싣지 않으므로 접근 로그에 남지 않는다.
 * 서버는 `callguard` 만 되돌려 준다(`SUBPROTOCOL`) — 토큰을 응답에 싣지 않는다.
 */
export function bearerFromSubprotocols(header: string | string[] | undefined): string | null {
  const joined = Array.isArray(header) ? header.join(",") : header;
  if (joined === undefined) {
    return null;
  }
  for (const item of joined.split(",")) {
    const value = item.trim();
    if (value.startsWith("bearer.") && value.length > "bearer.".length) {
      return value.slice("bearer.".length);
    }
  }
  return null;
}

/** 서브프로토콜로 토큰을 낸 브라우저에게 되돌려 줄 이름. 이게 없으면 크롬이 핸드셰이크를 끊는다. */
export const SUBPROTOCOL = "callguard";

/** `Authorization: Bearer <토큰>` 에서 토큰만. 없거나 다른 방식이면 null. */
export function bearerToken(header: string | undefined): string | null {
  if (header === undefined) {
    return null;
  }
  const match = /^Bearer\s+(\S+)\s*$/i.exec(header);
  return match?.[1] ?? null;
}
