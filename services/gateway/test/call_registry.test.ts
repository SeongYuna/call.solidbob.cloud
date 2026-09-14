// Requirement: A-1, A-2, A-3, COST-1, SEC-1
import { test } from "node:test";
import assert from "node:assert/strict";
import { BudgetGuard } from "../src/app/budget_guard.ts";
import { CallRegistry, type Channel } from "../src/app/call_registry.ts";
import { localDay } from "../src/domain/budget.ts";
import { CaptureBroadcaster, FakeHub, FakeStt, MemoryLedger, newLog, silence, tick } from "./fakes.ts";

const RAW_PII = "주민번호 900101-1234567 입니다";

function setup(opts: { ledger?: Record<string, number>; caps?: { perDay: number; perMonth: number } } = {}) {
  const hub = new FakeHub();
  const stt = new FakeStt();
  const broadcaster = new CaptureBroadcaster();
  const log = newLog();
  let now = 1_000_000;
  const budget = new BudgetGuard(
    new MemoryLedger(opts.ledger ?? {}),
    opts.caps ?? { perDay: 600, perMonth: 3600 },
    () => new Date(),
    log,
    1000,
  );
  const registry = new CallRegistry({
    hub,
    stt,
    budget,
    broadcaster,
    log,
    nowMs: () => now,
    drainTimeoutMs: 500,
  });
  return {
    hub,
    stt,
    broadcaster,
    log,
    budget,
    registry,
    advance: (ms: number) => {
      now += ms;
    },
  };
}

async function openOk(registry: CallRegistry, callId: string, speaker: "agent" | "customer", channelCount = 1): Promise<Channel> {
  const result = await registry.open({ callId, speaker, sampleRate: 16000, channelCount });
  assert.equal(result.ok, true, result.ok ? "" : result.reason);
  return (result as { ok: true; channel: Channel }).channel;
}

test("통화를 처음 여는 순간 서버에 통화 행을 만든다 — 화자가 둘이어도 한 번", async () => {
  const { registry, hub } = setup();
  await openOk(registry, "test-1", "agent", 2);
  await openOk(registry, "test-1", "customer", 2);
  assert.equal(hub.calls.length, 1);
  assert.deepEqual(hub.calls[0], { call_id: "test-1", stt_engine: "fake-stt", channel_count: 2 });
});

test("같은 통화의 같은 화자 채널을 두 번 열지 않는다", async () => {
  const { registry } = setup();
  await openOk(registry, "test-1", "agent");
  const second = await registry.open({ callId: "test-1", speaker: "agent", sampleRate: 16000, channelCount: 1 });
  assert.equal(second.ok, false);
  assert.equal(second.ok ? "" : second.kind, "busy");
});

test("서버에 통화를 못 열면 채널도 열지 않는다 (외래키 때문에 저장이 전부 실패한다)", async () => {
  const { registry, hub, stt } = setup();
  hub.failStart = 503;
  const result = await registry.open({ callId: "test-1", speaker: "agent", sampleRate: 16000, channelCount: 1 });
  assert.equal(result.ok, false);
  assert.equal(stt.streams.length, 0);
  assert.equal(registry.activeCalls, 0);
});

test("STT 를 쓸 수 없으면 서버에 통화 행을 만들기 전에 거절한다", async () => {
  const { registry, hub, stt } = setup();
  stt.unavailableReason = "키 없음";
  const result = await registry.open({ callId: "test-1", speaker: "agent", sampleRate: 16000, channelCount: 1 });
  assert.equal(result.ok, false);
  assert.equal(hub.calls.length, 0);
});

test("interim 은 같은 번호, final 뒤에는 새 번호 — 번호는 통화 안에서 화자와 무관하게 이어진다", async () => {
  const { registry, hub, stt } = setup();
  const agent = await openOk(registry, "test-1", "agent", 2);
  const customer = await openOk(registry, "test-1", "customer", 2);
  const agentStt = stt.streams[0]!;
  const customerStt = stt.streams[1]!;

  agentStt.emit("네 다산", false, 400);
  agentStt.emit("네 다산콜센터입니다", true, 900);
  customerStt.emit("전입신고", true, 1500);
  agentStt.emit("무엇을 도와드릴까요", true, 2500);
  await agent.close();
  await customer.close();

  const byText = Object.fromEntries(hub.ingested.map((raw) => [raw.text, raw.segment_id]));
  assert.equal(byText["네 다산"], byText["네 다산콜센터입니다"]);
  assert.equal(byText["네 다산콜센터입니다"], 1);
  assert.equal(byText["전입신고"], 2);
  assert.equal(byText["무엇을 도와드릴까요"], 3);
  assert.deepEqual(
    hub.ingested.map((raw) => raw.speaker),
    hub.ingested.map((raw) => (raw.text === "전입신고" ? "customer" : "agent")),
  );
});

test("utterance_end_ms 는 통화 시작 기준이다 — 늦게 붙은 채널은 그만큼 더한다", async () => {
  const { registry, hub, stt, advance } = setup();
  const agent = await openOk(registry, "test-1", "agent", 2);
  advance(3000);
  const customer = await openOk(registry, "test-1", "customer", 2);
  stt.streams[0]!.emit("상담원", true, 1000);
  stt.streams[1]!.emit("고객", true, 1000);
  await agent.close();
  await customer.close();
  const at = Object.fromEntries(hub.ingested.map((raw) => [raw.speaker, raw.utterance_end_ms]));
  assert.equal(at["agent"], 1000);
  assert.equal(at["customer"], 4000);
});

test("SEC-1 — 대시보드로는 서버가 마스킹한 응답만 간다", async () => {
  const { registry, broadcaster, stt } = setup();
  const channel = await openOk(registry, "test-1", "customer");
  stt.last().emit(RAW_PII, true, 1200);
  await channel.close();

  const published = JSON.stringify(broadcaster.messages);
  assert.ok(!published.includes("900101"), "원문 숫자가 대시보드 메시지에 있다");
  const transcript = broadcaster.ofType("transcript")[0];
  assert.equal(transcript?.payload.text, "주민번호 ******-******* 입니다");
});

test("SEC-1 — 서버가 실패하면 그 결과는 아무 데도 가지 않고, 로그에 원문이 없다", async () => {
  const { registry, broadcaster, hub, stt, log } = setup();
  hub.failIngest = 501;
  const channel = await openOk(registry, "test-1", "customer");
  stt.last().emit(RAW_PII, true, 1200);
  await channel.close();

  assert.equal(broadcaster.messages.length, 0);
  assert.equal(hub.recommended.length, 0, "마스킹 안 된 본문으로 추천을 부르지 않는다");
  assert.ok(log.warnings.some((line) => line.includes("status=501")));
  assert.ok(!log.warnings.join("\n").includes("900101"), "원문이 로그에 있다");
});

test("final 이면 마스킹된 본문으로 추천을 요청하고 결과를 흘린다", async () => {
  const { registry, broadcaster, hub, stt } = setup();
  const channel = await openOk(registry, "test-1", "customer");
  stt.last().emit("등본 발급 1건", false, 600);
  stt.last().emit("등본 발급 1건 하려고요", true, 1200);
  await channel.close();

  assert.equal(hub.recommended.length, 1, "interim 으로는 추천하지 않는다");
  assert.equal(hub.recommended[0]?.text, "등본 발급 *건 하려고요");
  assert.equal(broadcaster.ofType("recommendation").length, 1);
});

test("fired:false 추천 응답도 그대로 흘린다 — 대시보드가 세 상태를 구분한다(decisions/401)", async () => {
  const { registry, broadcaster, hub, stt } = setup();
  hub.fired = false;
  const channel = await openOk(registry, "test-1", "agent");
  stt.last().emit("네 알겠습니다", true, 800);
  await channel.close();
  assert.equal(broadcaster.ofType("recommendation")[0]?.payload["fired"], "false");
});

test("빈 결과는 서버에 보내지 않는다", async () => {
  const { registry, hub, stt } = setup();
  const channel = await openOk(registry, "test-1", "agent");
  stt.last().emit("   ", true, 800);
  await channel.close();
  assert.equal(hub.ingested.length, 0);
});

test("COST-1 — 캡에 닿으면 오디오를 보내지 않고 채널을 닫는다", async () => {
  const { registry, stt } = setup({ ledger: { [localDay(new Date())]: 598 } });
  const channel = await openOk(registry, "test-1", "agent");
  const reasons: string[] = [];
  channel.onStop((reason) => reasons.push(reason));

  assert.equal(channel.pushAudio(silence(1.5)), true);
  assert.equal(channel.pushAudio(silence(1.0)), false);
  assert.equal(stt.last().bytes, silence(1.5).byteLength, "캡을 넘는 오디오가 STT 로 갔다");
  assert.equal(stt.last().ended, true);
  assert.match(reasons[0] ?? "", /한도/);
});

test("COST-1 — 캡을 넘겼으면 새 채널을 열지 않는다", async () => {
  const { registry, hub } = setup({ ledger: { [localDay(new Date())]: 600 } });
  const result = await registry.open({ callId: "test-1", speaker: "agent", sampleRate: 16000, channelCount: 1 });
  assert.equal(result.ok, false);
  assert.equal(result.ok ? "" : result.kind, "budget");
  assert.equal(hub.calls.length, 0);
});

test("채널을 닫으면 쓴 초를 장부에 쓰고 통화를 비운다", async () => {
  const { registry, budget } = setup();
  const channel = await openOk(registry, "test-1", "agent");
  channel.pushAudio(silence(2));
  await channel.close();
  await tick();
  assert.equal(registry.activeCalls, 0);
  assert.equal(budget.snapshot().usedTodaySeconds, 2);
});

test("STT 오류는 채널을 닫고 이유를 알린다", async () => {
  const { registry, stt } = setup();
  const channel = await openOk(registry, "test-1", "agent");
  const reasons: string[] = [];
  channel.onStop((reason) => reasons.push(reason));
  stt.last().handlers.onFatal("code=7");
  await tick();
  assert.match(reasons[0] ?? "", /STT 오류/);
  assert.equal(channel.pushAudio(silence(0.1)), false);
});

// ── 글자 채널 (/dev, decisions/109) ──

test("글자 채널 — 구글을 부르지 않고, 통화 기록에 엔진을 web-speech 로 적는다", async () => {
  const { registry, hub, stt, broadcaster } = setup();
  const result = await registry.open({ callId: "test-t", speaker: "customer", sampleRate: 16000, channelCount: 1, source: "text" });
  assert.equal(result.ok, true);
  const channel = (result as { ok: true; channel: Channel }).channel;
  assert.equal(stt.streams.length, 0, "글자 채널이 STT 스트림을 열었다");
  assert.equal(hub.calls[0]?.stt_engine, "web-speech");

  assert.equal(channel.pushText("전입신고 서류", false), true);
  assert.equal(channel.pushText("전입신고 서류 뭐 필요해요 010-1234-5678", true), true);
  assert.equal(channel.pushAudio(silence(0.1)), false, "글자 채널은 오디오를 받지 않는다");
  await channel.close();

  assert.deepEqual(hub.ingested.map((r) => [r.segment_id, r.is_final]), [[1, false], [1, true]]);
  const published = JSON.stringify(broadcaster.messages);
  assert.ok(!published.includes("1234"), "SEC-1 — 글자 채널도 서버 마스킹을 거친 것만 흘린다");
  assert.equal(hub.recommended[0]?.text, "전입신고 서류 뭐 필요해요 ***-****-****");
});

test("글자 채널은 STT 캡과 무관하다 — 캡이 비어 있어도 열린다", async () => {
  const { registry, budget } = setup({ caps: { perDay: 0, perMonth: 0 } });
  const result = await registry.open({ callId: "test-t2", speaker: "agent", sampleRate: 16000, channelCount: 1, source: "text" });
  assert.equal(result.ok, true);
  const channel = (result as { ok: true; channel: Channel }).channel;
  channel.pushText("네", true);
  await channel.close();
  assert.equal(budget.snapshot().usedTodaySeconds, 0);
});

test("글자 채널은 구글 키가 없어도 열린다", async () => {
  const { registry, stt } = setup();
  stt.unavailableReason = "키 없음";
  const result = await registry.open({ callId: "test-t3", speaker: "agent", sampleRate: 16000, channelCount: 1, source: "text" });
  assert.equal(result.ok, true);
  await (result as { ok: true; channel: Channel }).channel.close();
});
