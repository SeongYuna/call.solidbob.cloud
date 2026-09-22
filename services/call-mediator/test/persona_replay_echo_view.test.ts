// Requirement: A-3, B-1, D-1, SEC-2
import assert from "node:assert/strict";
import { test } from "node:test";
import { closeAuth } from "../scripts/persona_replay/close_auth.ts";
import { describeMissing, FinalEchoTracker } from "../scripts/persona_replay/final_echo.ts";
import { formatLatency, formatRecommendation } from "../scripts/persona_replay/ws_view.ts";

test("보낸 확정이 화자별로 전부 돌아오면 풀린다 — 순서가 섞여도, 같은 segment 는 한 번만 센다", async () => {
  const echo = new FinalEchoTracker();
  echo.noteSent("agent");
  echo.noteSent("customer");
  echo.noteSent("agent");
  const waiting = echo.whenAllEchoed(1_000);
  echo.noteEcho("customer", 2);
  echo.noteEcho("agent", 1);
  echo.noteEcho("agent", 1); // 같은 발화가 두 번 와도 하나다
  assert.equal(echo.complete(), false);
  echo.noteEcho("agent", 3);
  const result = await waiting;
  assert.equal(result.ok, true);
  assert.deepEqual(result.missing, { agent: 0, customer: 0 });
});

test("마지막 확정이 돌아오지 않으면 상한에서 ok:false 로 풀리고 무엇이 빠졌는지 말한다 — 예외로 멈추지 않는다", async () => {
  const echo = new FinalEchoTracker();
  for (const speaker of ["agent", "customer", "agent", "customer", "agent"] as const) {
    echo.noteSent(speaker);
  }
  [1, 2, 3, 4].forEach((seg, i) => echo.noteEcho(i % 2 === 0 ? "agent" : "customer", seg));
  const result = await echo.whenAllEchoed(20);
  assert.equal(result.ok, false);
  assert.deepEqual(result.missing, { agent: 1, customer: 0 });
  assert.match(describeMissing(result), /상담원 1건이 \d+초 안에 \/ws 로 돌아오지 않았다/);
});

test("이미 다 돌아왔으면 기다리지 않는다", async () => {
  const echo = new FinalEchoTracker();
  const result = await echo.whenAllEchoed(60_000);
  assert.equal(result.ok, true);
  assert.equal(result.waitedMs < 1_000, true);
});

test("추천 줄에 지연 구간을 찍는다 — 없는 값은 0 이 아니라 —", () => {
  const line = formatRecommendation({
    fired: "true",
    cards: [{ title: "2.12 광역 교통" }],
    retrieval_ms: "412",
    generation_ms: null,
    internal_latency_ms: "530.4",
    e2e_latency_ms: "611",
  });
  assert.equal(line, '추천 fired=true ["2.12 광역 교통"] | 검색 412ms · 생성 — · 내부 530ms · e2e 611ms(STT 미경유)');
  assert.equal(formatLatency({ fired: "false" }), "검색 — · 생성 — · 내부 — · e2e —");
});

test("/close 토큰 — 상담원 토큰이 먼저, 없으면 서비스 토큰, 둘 다 없으면 헤더 없음. 출처는 변수 이름만", () => {
  const both = closeAuth({ CALL_AGENT_TOKEN: " cga_x ", CORE_API_TOKEN: "svc" });
  assert.deepEqual(both, { headers: { authorization: "Bearer cga_x" }, source: "CALL_AGENT_TOKEN" });
  assert.deepEqual(closeAuth({ CORE_API_TOKEN: "svc", CALL_AGENT_TOKEN: "  " }), {
    headers: { authorization: "Bearer svc" },
    source: "CORE_API_TOKEN",
  });
  assert.deepEqual(closeAuth({}), { headers: {}, source: null });
});
