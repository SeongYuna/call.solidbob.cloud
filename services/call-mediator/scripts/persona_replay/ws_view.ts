// Requirement: B-1, A-3
/**
 * `--watch` 가 찍는 `/ws` 한 줄 — 순수 함수라 테스트가 스택 없이 돈다.
 *
 * 추천(`recommendation`)에는 콜 미디에이터가 서버 응답을 **펼쳐** 싣는다(`call_registry.ts` `withE2eLatency`) — 그래서
 * `retrieval_ms`·`generation_ms`·`internal_latency_ms`·`e2e_latency_ms` 가 `/ws` 에 이미 있다. 전에는 카드 제목만 찍어서
 * 운영 확인 때 이 값을 `/record`(상한인 `internal_latency_ms`)로 돌아가 읽었다(2026-09-22 류준 05번 기록).
 * 값은 계약대로 **문자열**이다(7.3절). 없으면 `—` 로 찍는다 — 0 으로 지어내지 않는다(절대 원칙 2).
 * ⚠ 합성 통화는 STT 를 거치지 않는다 — `e2e` 는 실제보다 짧다(`decisions/209`). 줄에 그 표시를 붙인다.
 */

const LATENCY_FIELDS: ReadonlyArray<readonly [string, string]> = [
  ["retrieval_ms", "검색"],
  ["generation_ms", "생성"],
  ["internal_latency_ms", "내부"],
  ["e2e_latency_ms", "e2e"],
];

function ms(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  const n = Number(value);
  return Number.isFinite(n) ? `${Math.round(n)}ms` : "—";
}

/** `검색 412ms · 생성 — · 내부 530ms · e2e 611ms(STT 미경유)` */
export function formatLatency(payload: Record<string, unknown>): string {
  const parts = LATENCY_FIELDS.map(([key, label]) => `${label} ${ms(payload[key])}`);
  const e2e = ms(payload["e2e_latency_ms"]) === "—" ? "" : "(STT 미경유)";
  return parts.join(" · ") + e2e;
}

/** 추천 한 줄 — 발동 여부 · 카드 제목 · 지연 구간. */
export function formatRecommendation(payload: Record<string, unknown>): string {
  const cards = Array.isArray(payload["cards"]) ? (payload["cards"] as Array<{ title?: unknown }>).map((c) => String(c?.title ?? "")) : [];
  return `추천 fired=${String(payload["fired"])} ${cards.length ? `${JSON.stringify(cards)} ` : ""}| ${formatLatency(payload)}`;
}
