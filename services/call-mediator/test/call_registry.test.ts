// Requirement: A-1, A-2, A-3, COST-1, SEC-1
import { test } from "node:test";
import assert from "node:assert/strict";
import { BudgetGuard } from "../src/app/budget_guard.ts";
import { CallRegistry, type Channel } from "../src/app/call_registry.ts";
import { localDay } from "../src/domain/budget.ts";
import { CaptureBroadcaster, FakeHub, FakeStt, MemoryLedger, newLog, silence, tick } from "./fakes.ts";

const RAW_PII = "주민번호 900101-1234567 입니다";

function setup(
  opts: {
    ledger?: Record<string, number>;
    caps?: { perDay: number; perMonth: number };
    announceStarted?: boolean;
    announcePending?: boolean;
    announceCallGuard?: boolean;
    announceCompliance?: boolean;
    announceClosure?: boolean;
    announceRouting?: boolean;
    routingCandidates?: string[];
    ingestRetryDelaysMs?: number[];
  } = {},
) {
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
    announceStarted: opts.announceStarted,
    announcePending: opts.announcePending,
    announceCallGuard: opts.announceCallGuard,
    announceCompliance: opts.announceCompliance,
    announceClosure: opts.announceClosure,
    announceRouting: opts.announceRouting,
    routingCandidates: opts.routingCandidates,
    // 테스트는 재시도 간격을 짧게 — 기본값(운영)은 call_registry.ts 의 INGEST_RETRY_DELAYS_MS
    ingestRetryDelaysMs: opts.ingestRetryDelaysMs ?? [1, 1],
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

test("announceStarted 가 꺼져 있으면(기본) started 를 안 보낸다", async () => {
  const { registry, broadcaster } = setup();
  await openOk(registry, "test-1", "agent");
  assert.equal(broadcaster.ofType("started").length, 0);
});

test("announceStarted 가 켜져 있으면 서버에 통화 행이 생기자마자 started 를 한 번 보낸다 — 화자가 둘이어도 한 번", async () => {
  const { registry, broadcaster } = setup({ announceStarted: true });
  await openOk(registry, "test-1", "agent", 2);
  await openOk(registry, "test-1", "customer", 2);
  const started = broadcaster.ofType("started");
  assert.equal(started.length, 1);
  assert.deepEqual(started[0]!.payload, { call_id: "test-1" });
});

test("서버가 통화 시작에 실패하면 started 를 보내지 않는다", async () => {
  const { registry, hub, broadcaster } = setup({ announceStarted: true });
  hub.failStart = 503;
  const result = await registry.open({ callId: "test-1", speaker: "agent", sampleRate: 16000, channelCount: 1 });
  assert.equal(result.ok, false);
  assert.equal(broadcaster.ofType("started").length, 0);
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

test("w6-segment-id-reuse — 다시 연 통화는 서버에 저장된 마지막 번호 다음부터 센다", async () => {
  // 2026-09-22 운영 QA test-qa-05: 채널을 닫았다 다시 열자 1번부터 다시 세어 저장된 상담원 인사를 고객 발화로 덮었다
  const { registry, hub, stt } = setup();
  hub.lastSegmentId = 6;
  const customer = await openOk(registry, "test-qa-05", "customer");
  stt.streams[0]!.emit("서류 준비해서 오늘 안에 다 끝내고 싶어서요", true, 500);
  stt.streams[0]!.emit("네", true, 900);
  await customer.close();
  assert.deepEqual(
    hub.ingested.map((raw) => raw.segment_id),
    [7, 8],
  );
});

test("w6-segment-id-reuse — 새 통화(마지막 번호 0)는 전처럼 1부터 센다", async () => {
  const { registry, hub, stt } = setup();
  const agent = await openOk(registry, "test-new", "agent");
  stt.streams[0]!.emit("안녕하세요", true, 300);
  await agent.close();
  assert.equal(hub.ingested[0]!.segment_id, 1);
});

test("w6-segment-id-reuse — 같은 프로세스에서 닫았다 다시 열어도 번호가 이어진다", async () => {
  // 프로세스 메모리의 통화 객체는 채널이 모두 닫히면 버려진다. 서버가 돌려준 번호로 이어 간다
  const { registry, hub, stt } = setup();
  const first = await openOk(registry, "test-qa-05", "agent");
  stt.streams[0]!.emit("안녕하세요 다산콜센터입니다", true, 300);
  await first.close();
  hub.lastSegmentId = Math.max(...hub.ingested.map((raw) => raw.segment_id)); // 서버가 저장한 만큼
  const again = await openOk(registry, "test-qa-05", "customer");
  stt.streams[1]!.emit("서류 준비해서 오늘 안에 다 끝내고 싶어서요", true, 400);
  await again.close();
  assert.deepEqual(
    hub.ingested.map((raw) => [raw.speaker, raw.segment_id]),
    [
      ["agent", 1],
      ["customer", 2],
    ],
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

test("추천 요청에 STT final 을 받은 시각을 싣는다 — 통화 시작 기준, 서버 대기 시간은 섞지 않는다", async () => {
  const { registry, hub, stt, advance } = setup();
  const agent = await openOk(registry, "test-1", "agent", 2);
  advance(2000);
  const customer = await openOk(registry, "test-1", "customer", 2);
  advance(1500); // 고객 채널이 열린 지 1.5초 — 통화 시작 기준 3.5초
  hub.ingestDelayMs = 20; // 서버가 느려도 도착 시각은 받은 순간 그대로다
  stt.streams[1]!.emit("전입신고 서류가 뭐예요", true, 1150);
  advance(5000);
  await customer.close();
  await agent.close();
  assert.equal(hub.recommended.length, 1);
  assert.equal(hub.recommended[0]!.utterance_end_ms, 3150);
  assert.equal(hub.recommended[0]!.received_at_ms, 3500);
});

test("「검색 중」 신호는 기본으로 보내지 않는다 — 대시보드 파서가 아직 모르는 type 이다", async () => {
  const { registry, stt, broadcaster } = setup();
  const customer = await openOk(registry, "test-1", "customer");
  stt.last().emit("여권 재발급 서류", true, 900);
  await customer.close();
  assert.equal(broadcaster.ofType("recommendation_pending").length, 0);
  assert.equal(broadcaster.ofType("recommendation").length, 1);
});

test("켜면 추천 요청 직전에 「검색 중」 을 보낸다 — 전사 뒤, 추천 앞, 값은 문자열", async () => {
  const { registry, stt, broadcaster } = setup({ announcePending: true });
  const customer = await openOk(registry, "test-1", "customer");
  stt.last().emit("여권 재발급 서류", false, 500);
  stt.last().emit("여권 재발급 서류가 뭐예요", true, 900);
  await customer.close();
  const types = broadcaster.messages.map((item) => item.message.type);
  assert.deepEqual(types.slice(-3), ["transcript", "recommendation_pending", "recommendation"]);
  assert.equal(broadcaster.ofType("recommendation_pending").length, 1); // interim 에는 없다
  assert.deepEqual(broadcaster.ofType("recommendation_pending")[0]!.payload, { call_id: "test-1", segment_id: "1" });
});

test("speaker=auto — 먼저 말한 화자를 상담원으로, 라벨 없는 interim 은 보내지 않고, 엔진 이름에 +diarize 를 남긴다", async () => {
  const { registry, hub, stt, broadcaster } = setup();
  const result = await registry.open({ callId: "test-1", speaker: "auto", sampleRate: 16000, channelCount: 1 });
  assert.equal(result.ok, true);
  const channel = (result as { ok: true; channel: Channel }).channel;
  assert.equal(stt.last().options.diarize, true);
  assert.equal(hub.calls[0]!.stt_engine, "fake-stt+diarize");

  stt.last().emit("네 다산", false, 500); // 라벨 없음 — 버린다
  stt.last().emit("네 다산콜센터입니다", true, 1200, "2");
  stt.last().emit("여권 재발급 서류가 뭐예요", true, 3000, "1");
  await channel.close();

  assert.deepEqual(
    hub.ingested.map((raw) => [raw.text, raw.speaker, raw.segment_id]),
    [
      ["네 다산콜센터입니다", "agent", 1],
      ["여권 재발급 서류가 뭐예요", "customer", 2],
    ],
  );
  assert.deepEqual(hub.recommended.map((r) => r.speaker), ["agent", "customer"]);
  assert.equal(broadcaster.ofType("transcript").length, 2);
});

test("speaker=auto 는 그 통화의 두 화자를 다 차지한다 — 다른 채널과 섞이지 않는다", async () => {
  const { registry } = setup();
  await openOk(registry, "test-1", "agent", 2);
  const auto = await registry.open({ callId: "test-1", speaker: "auto", sampleRate: 16000, channelCount: 1 });
  assert.equal(auto.ok ? "" : auto.kind, "busy");

  const other = await registry.open({ callId: "test-2", speaker: "auto", sampleRate: 16000, channelCount: 1 });
  assert.equal(other.ok, true);
  const customer = await registry.open({ callId: "test-2", speaker: "customer", sampleRate: 16000, channelCount: 1 });
  assert.equal(customer.ok ? "" : customer.kind, "busy");
});

test("speaker=auto 는 글자 채널에서 거절한다 — 가를 소리가 없다", async () => {
  const { registry, hub } = setup();
  const result = await registry.open({ callId: "test-1", speaker: "auto", sampleRate: 16000, channelCount: 1, source: "text" });
  assert.equal(result.ok, false);
  assert.equal(hub.calls.length, 0);
});

test("C-6 — 고객 final 만, 마스킹된 본문으로 콜 가드를 검사한다. 상담원·interim 은 부르지 않는다", async () => {
  const { registry, hub, stt } = setup();
  const agent = await openOk(registry, "test-1", "agent", 2);
  const customer = await openOk(registry, "test-1", "customer", 2);
  stt.streams[0]!.emit("병신이라뇨 고객님", true, 500); // 상담원 — 검사 대상 아님
  stt.streams[1]!.emit("이 병신", false, 900); // interim — 검사 대상 아님
  stt.streams[1]!.emit("이 병신 같은 010-1234-5678", true, 1200);
  await agent.close();
  await customer.close();
  assert.equal(hub.guarded.length, 1);
  assert.equal(hub.guarded[0]!.customer_utterance, "이 병신 같은 ***-****-****"); // 원문 번호가 없다 (SEC-1)
  assert.equal(hub.guarded[0]!.segment_id, 2);
});

test("C-6 — 잡힌 신호를 기본으로는 대시보드에 보내지 않는다 (검사는 한다)", async () => {
  const { registry, hub, stt, broadcaster } = setup();
  const customer = await openOk(registry, "test-1", "customer");
  stt.last().emit("이 병신 같은", true, 900);
  await customer.close();
  assert.equal(hub.guarded.length, 1);
  assert.equal(broadcaster.ofType("call_guard").length, 0);
});

test("C-6 — 켜면 잡힌 신호만 call_guard 로 보낸다. 잡힌 것이 없거나 서버가 실패하면 보내지 않는다", async () => {
  const { registry, hub, stt, broadcaster, log } = setup({ announceCallGuard: true });
  const customer = await openOk(registry, "test-1", "customer");
  stt.last().emit("이 병신 같은", true, 900);
  stt.last().emit("여권 재발급 서류요", true, 2000);
  await tick(10);
  hub.failGuard = 501;
  stt.last().emit("또 병신", true, 3000);
  await customer.close();
  const sent = broadcaster.ofType("call_guard");
  assert.equal(sent.length, 1);
  assert.deepEqual(sent[0]!.payload.flags, [
    { category: "insult", phrase: "병신", span: ["2", "4"], source_doc_id: "DASAN-MANUAL-5.1" },
  ]);
  assert.ok(log.warnings.some((w) => w.includes("콜 가드 검사 실패") && w.includes("501")));
});

test("발신 번호는 통화를 처음 여는 채널 것만 통화 시작에 싣고, 로그에 남기지 않는다 (decisions/304)", async () => {
  const { registry, hub, log } = setup();
  await registry.open({ callId: "test-1", speaker: "agent", sampleRate: 16000, channelCount: 2, callerPhone: "010-1234-5678" });
  await registry.open({ callId: "test-1", speaker: "customer", sampleRate: 16000, channelCount: 2, callerPhone: "010-9999-9999" });
  await registry.open({ callId: "test-2", speaker: "agent", sampleRate: 16000, channelCount: 1 });
  assert.equal(hub.calls[0]!.caller_phone, "010-1234-5678");
  assert.equal(hub.calls.length, 2);
  assert.equal("caller_phone" in hub.calls[1]!, false);
  assert.ok(log.warnings.every((w) => !w.includes("1234")));
});

test("F-2 — 추천 1순위 조항을 절차로 잡고, 상담원 확정 발화가 쌓일 때마다 마스킹본으로 다시 판정한다 (기본은 화면에 안 보낸다)", async () => {
  const { registry, hub, stt, broadcaster } = setup();
  hub.topDocId = "DASAN-TERM-4.3";
  const agent = await openOk(registry, "test-1", "agent", 2);
  const customer = await openOk(registry, "test-1", "customer", 2);
  stt.streams[1]!.emit("초본 떼려면 뭐 필요해요", true, 1000);
  await tick(20);
  stt.streams[0]!.emit("신분증 지참하시고 010-1234-5678 로", true, 2000);
  await agent.close();
  await customer.close();

  assert.deepEqual(hub.docsChecked.map((r) => [r.procedure, r.agent_utterances]), [
    ["DASAN-TERM-4.3", []],
    ["DASAN-TERM-4.3", ["신분증 지참하시고 ***-****-**** 로"]], // 마스킹본만 (SEC-1)
  ]);
  assert.equal(broadcaster.ofType("closure").length, 0);
});

test("F-2 — 켜면 판정을 순서대로 closure 로 보내고, 규칙 없는 조항(422)은 다시 묻지 않는다", async () => {
  const { registry, hub, stt, broadcaster, log } = setup({ announceClosure: true });
  hub.topDocId = "DASAN-TERM-4.3";
  const agent = await openOk(registry, "test-1", "agent", 2);
  const customer = await openOk(registry, "test-1", "customer", 2);
  stt.streams[1]!.emit("초본 서류요", true, 1000);
  await tick(20);
  stt.streams[0]!.emit("신분증 가져오세요", true, 2000);
  await tick(20);
  hub.topDocId = "DASAN-TERM-2.6";
  hub.notProcedures.add("DASAN-TERM-2.6");
  stt.streams[1]!.emit("교통카드도요", true, 3000);
  await tick(20);
  stt.streams[0]!.emit("네 알겠습니다", true, 4000);
  await agent.close();
  await customer.close();

  const verdicts = broadcaster.ofType("closure").map((m) => [m.payload.procedure, m.payload["verdict"]]);
  assert.deepEqual(verdicts.slice(0, 2), [["DASAN-TERM-4.3", "incomplete"], ["DASAN-TERM-4.3", "complete"]]);
  assert.ok(verdicts.every(([procedure]) => procedure === "DASAN-TERM-4.3"));
  assert.equal(hub.docsChecked.filter((r) => r.procedure === "DASAN-TERM-2.6").length, 0);
  assert.ok(log.warnings.every((w) => !w.includes("필요서류 판정 실패")));
});

test("C-1~C-4 — 상담원 확정 발화만 마스킹본으로 검사한다. 고객 발화는 검사하지 않고, 기본으로는 화면에 안 보낸다", async () => {
  const { registry, hub, stt, broadcaster } = setup();
  const agent = await openOk(registry, "test-1", "agent", 2);
  const customer = await openOk(registry, "test-1", "customer", 2);
  stt.streams[1]!.emit("연납 되나요", true, 1000);
  await tick(20);
  stt.streams[0]!.emit("무조건 됩니다 010-1234-5678", true, 2000);
  await agent.close();
  await customer.close();

  assert.deepEqual(
    hub.complianceChecked.map((r) => [r.segment_id, r.agent_utterance]),
    [[2, "무조건 됩니다 ***-****-****"]], // 상담원 발화만, 마스킹본만 (SEC-1)
  );
  assert.equal(broadcaster.ofType("compliance").length, 0);
});

test("C-1~C-4 — 켜면 잡힌 위반은 compliance 로, 검사 실패는 compliance_unavailable 로 보낸다. 위반 없음은 침묵. 통화는 계속된다", async () => {
  const { registry, hub, stt, broadcaster, log } = setup({ announceCompliance: true });
  const agent = await openOk(registry, "test-1", "agent");
  stt.last().emit("무조건 됩니다", true, 1000);
  stt.last().emit("신분증 가져오세요", true, 2000);
  await tick(10);
  hub.failCompliance = 503;
  stt.last().emit("무조건 감면돼요", true, 3000);
  await tick(10);
  hub.failCompliance = 501; // 스포크 미등록 — 탐지 자체가 없다
  stt.last().emit("확실히 됩니다", true, 4000);
  await agent.close();

  const sent = broadcaster.ofType("compliance");
  assert.equal(sent.length, 1); // 위반 없음(2번)은 아무 메시지도 아니다
  assert.deepEqual(sent[0]!.payload.findings, [
    { rule_code: "C-1", phrase: "무조건", alternative_source: { doc_id: "DASAN-TERM-1.4", title: "권장 대체 표현" } },
  ]);
  // 실패한 발화 둘은 「검사 못 함」으로 따로 알린다 — 「위반 없음」과 구분돼야 화면이 탐지 미동작을 초록으로 두지 않는다
  assert.deepEqual(
    broadcaster.ofType("compliance_unavailable").map((m) => m.payload),
    [
      { call_id: "test-1", segment_id: "3", status: "503" },
      { call_id: "test-1", segment_id: "4", status: "501" },
    ],
  );
  assert.equal(broadcaster.ofType("transcript").length, 4); // 실패한 발화의 자막도 나갔다
  assert.ok(log.warnings.some((w) => w.includes("컴플라이언스 검사 실패") && w.includes("503")));
});

test("C-1~C-4 — 꺼져 있으면 검사 실패도 화면에 알리지 않는다(경고 로그만)", async () => {
  const { registry, hub, stt, broadcaster, log } = setup();
  hub.failCompliance = 503;
  const agent = await openOk(registry, "test-1", "agent");
  stt.last().emit("무조건 됩니다", true, 1000);
  await agent.close();

  assert.equal(broadcaster.ofType("compliance_unavailable").length, 0);
  assert.ok(log.warnings.some((w) => w.includes("컴플라이언스 검사 실패")));
});

test("F-2 — 1순위 카드가 규칙 없는 조항(422)이면 아래 카드로 내려가지 않고 아무것도 잡지 않는다 (w6-procedure-pick-rule)", async () => {
  const { registry, hub, stt, broadcaster } = setup({ announceClosure: true });
  hub.cardDocIds = ["DASAN-POLICY-1", "DASAN-TERM-4.4", "DASAN-TERM-6.2", "DASAN-TERM-4.3"];
  hub.notProcedures.add("DASAN-POLICY-1");
  const agent = await openOk(registry, "test-1", "agent", 2);
  const customer = await openOk(registry, "test-1", "customer", 2);
  stt.streams[1]!.emit("재난지원금 뭐 필요해요", true, 1000);
  await tick(30);
  stt.streams[0]!.emit("신분증 가져오세요", true, 2000);
  await tick(30);
  // 다음 추천도 같은 1순위면 다시 묻지 않는다(422 를 이미 들었다)
  stt.streams[1]!.emit("그리고요", true, 3000);
  await agent.close();
  await customer.close();

  // 1순위만 한 번 묻는다. 규칙 있는 2순위(4.4)·3순위(6.2)는 묻지도 않는다
  assert.deepEqual(hub.docsAsked, ["DASAN-POLICY-1"]);
  assert.equal(hub.docsChecked.length, 0);
  assert.equal(broadcaster.ofType("closure").length, 0);
});

test("F-2 — 1순위 카드에 규칙이 있으면 그대로 절차로 잡고, 상담원 발화마다 다시 판정한다 (w6-procedure-pick-rule)", async () => {
  const { registry, hub, stt, broadcaster } = setup({ announceClosure: true });
  hub.cardDocIds = ["DASAN-TERM-6.2", "DASAN-TERM-4.4", "DASAN-TERM-4.3"];
  const agent = await openOk(registry, "test-1", "agent", 2);
  const customer = await openOk(registry, "test-1", "customer", 2);
  stt.streams[1]!.emit("재난지원금 뭐 필요해요", true, 1000);
  await tick(30);
  stt.streams[0]!.emit("신분증 가져오세요", true, 2000);
  await agent.close();
  await customer.close();

  assert.deepEqual(hub.docsAsked, ["DASAN-TERM-6.2", "DASAN-TERM-6.2"]);
  assert.deepEqual(
    broadcaster.ofType("closure").map((m) => [m.payload.procedure, m.payload["verdict"]]),
    [["DASAN-TERM-6.2", "incomplete"], ["DASAN-TERM-6.2", "complete"]],
  );
});

test("F-2 회귀 — SYN-010: 1순위 2.12(규칙 없음)면 5순위 2.9(규칙 있음)를 잡아 「신분증」을 빠졌다고 하지 않는다", async () => {
  // 09-22 운영: [2.12, 2.8, 2.10, 2.1, 2.9] 에서 규칙 있는 첫 조항 2.9(분실물 수령)를 잡아 incomplete 「신분증」을 띄웠다
  const { registry, hub, stt, broadcaster } = setup({ announceClosure: true });
  hub.cardDocIds = ["DASAN-TERM-2.12", "DASAN-TERM-2.8", "DASAN-TERM-2.10", "DASAN-TERM-2.1", "DASAN-TERM-2.9"];
  for (const id of ["DASAN-TERM-2.12", "DASAN-TERM-2.8", "DASAN-TERM-2.10", "DASAN-TERM-2.1"]) {
    hub.notProcedures.add(id);
  }
  const agent = await openOk(registry, "test-1", "agent", 2);
  const customer = await openOk(registry, "test-1", "customer", 2);
  stt.streams[1]!.emit("광역버스 환승 할인 되나요", true, 1000);
  await tick(30);
  stt.streams[0]!.emit("네 확인해 드릴게요", true, 2000);
  await agent.close();
  await customer.close();

  assert.deepEqual(hub.docsAsked, ["DASAN-TERM-2.12"]);
  assert.equal(hub.docsChecked.some((r) => r.procedure === "DASAN-TERM-2.9"), false);
  assert.equal(broadcaster.ofType("closure").length, 0);
});

test("추천을 방송할 때 e2e_latency_ms 를 채운다 — 발화 종료 → 방송 직전 (decisions/119)", async () => {
  // 서버 DTO·DB 컬럼은 09-09 부터 있었는데 아무도 값을 안 넣어 늘 null 이었다. 방송 시각을 아는 곳은 여기 하나다.
  const { registry, broadcaster, hub, stt, advance } = setup();
  const channel = await openOk(registry, "test-1", "customer");
  stt.last().emit("등본 발급 하려고요", true, 1200);      // 발화 종료 1,200ms
  advance(1500);                                          // 통화 시계가 1,500ms 흘렀다
  await channel.close();

  const payload = broadcaster.ofType("recommendation")[0]!.payload;
  assert.equal(typeof payload["e2e_latency_ms"], "string", "서버 응답처럼 문자열로 싣는다(7.3절)");
  assert.ok(Number(payload["e2e_latency_ms"]) >= 0);
});

test("발동하지 않은 추천에는 e2e_latency_ms 를 넣지 않는다", async () => {
  const { registry, broadcaster, hub, stt } = setup();
  hub.fired = false;
  const channel = await openOk(registry, "test-1", "agent");
  stt.last().emit("네 알겠습니다", true, 800);
  await channel.close();
  assert.equal("e2e_latency_ms" in broadcaster.ofType("recommendation")[0]!.payload, false);
});

test("withE2eLatency — 방송 시각에서 발화 종료 시각을 뺀다. 없는 값은 지어내지 않는다", async () => {
  const { withE2eLatency } = await import("../src/app/call_registry.ts");
  const fired = { fired: "true", cards: [] };
  assert.equal(withE2eLatency(fired, 1200, 2440)["e2e_latency_ms"], "1240");
  assert.equal(withE2eLatency(fired, 3000, 2000)["e2e_latency_ms"], "0", "시계가 어긋나도 음수를 내지 않는다");
  assert.equal("e2e_latency_ms" in withE2eLatency(fired, null, 2440), false, "발화 종료 시각이 없으면 넣지 않는다");
  assert.equal("e2e_latency_ms" in withE2eLatency(fired, undefined, 2440), false);
  assert.equal("e2e_latency_ms" in withE2eLatency({ fired: "false" }, 1200, 2440), false, "카드가 없으면 「표시까지」가 없다");
  assert.equal(withE2eLatency(fired, 1200, 2440) === fired, false, "원본을 고치지 않는다");
});

test("J-5 — 통화 시작이 성공하면 배정 판정을 한 번 부른다 · 후보는 설정 목록 (decisions/126)", async () => {
  const { registry, hub } = setup({ routingCandidates: ["agent-demo-1", "agent-demo-2"] });
  await openOk(registry, "test-1", "agent", 2);
  await openOk(registry, "test-1", "customer", 2); // 두 번째 채널은 같은 통화다 — 다시 부르지 않는다
  await tick(10);
  assert.deepEqual(hub.routed, [{ call_id: "test-1", candidates: ["agent-demo-1", "agent-demo-2"] }]);
});

test("J-5 — 후보 설정이 없으면 빈 목록을 보낸다 (서버가 기존 배정 규칙으로 떨어뜨린다)", async () => {
  const { registry, hub } = setup();
  await openOk(registry, "test-1", "agent");
  await tick(10);
  assert.deepEqual(hub.routed, [{ call_id: "test-1", candidates: [] }]);
});

test("J-5 — 통화 시작이 실패하면 배정 판정을 부르지 않는다 (서버가 404 를 낼 뿐이다)", async () => {
  const { registry, hub } = setup();
  hub.failStart = 503;
  await registry.open({ callId: "test-1", speaker: "agent", sampleRate: 16000, channelCount: 1 });
  await tick(10);
  assert.equal(hub.routed.length, 0);
});

test("J-5 — 배정 판정이 실패해도 통화는 그대로 돈다 · 로그에 상태만 남긴다", async () => {
  const { registry, hub, stt, log } = setup();
  hub.failRouting = 500;
  const agent = await openOk(registry, "test-1", "agent");
  stt.streams[0]!.emit("안녕하세요", true, 1000);
  await agent.close();
  assert.equal(hub.ingested.length, 1);
  assert.ok(log.warnings.some((w) => w.includes("배정 판정 실패") && w.includes("call=test-1") && w.includes("500")));
});

test("J-5 — announceRouting 이 꺼져 있으면(기본) routing_decision 을 안 보낸다", async () => {
  const { registry, broadcaster } = setup();
  await openOk(registry, "test-1", "agent");
  await tick(10);
  assert.equal(broadcaster.ofType("routing_decision").length, 0);
});

test("J-5 — announceRouting 이 켜져 있으면 판정 결과를 그대로 방송한다 (w6-routing-result-ui)", async () => {
  const { registry, broadcaster } = setup({ announceRouting: true });
  await openOk(registry, "test-1", "agent");
  await tick(10);
  const routed = broadcaster.ofType("routing_decision");
  assert.equal(routed.length, 1);
  assert.deepEqual(routed[0]!.payload, {
    call_id: "test-1",
    assigned_agent_id: null,
    is_blacklisted: "false",
    fell_back: "false",
  });
});

test("J-5 — announceRouting 이 켜져 있어도 판정이 실패하면 방송하지 않는다", async () => {
  const { registry, hub, broadcaster } = setup({ announceRouting: true });
  hub.failRouting = 500;
  await openOk(registry, "test-1", "agent");
  await tick(10);
  assert.equal(broadcaster.ofType("routing_decision").length, 0);
});

// ── 확정 전사 재시도 (w6-replay-last-turn, 2026-09-22 운영 SYN-010 마지막 턴 4/5) ─────────────────────────────
// 운영에서 마지막 상담원 확정이 콜 미디에이터까지 왔는데(재생기 쪽 소켓은 정상 1000 으로 닫혔다) 서버 전사 요청이 한 번
// 실패해 DB·/ws 어디에도 남지 않았다. 전에는 한 번 실패하면 그대로 버렸다. 서버 저장은 (call_id, segment_id) UPSERT 라
// 같은 확정을 다시 보내도 행이 하나다(decisions/205) — 확정은 몇 번 더 보낸다.

test("확정 전사가 한 번 503 으로 실패하면 다시 보내 저장·자막·「검색 중」까지 간다", async () => {
  const { registry, hub, stt, broadcaster, log } = setup({ announcePending: true });
  const channel = await openOk(registry, "test-1", "agent");
  hub.ingestFailQueue.push(503);
  stt.last().emit("네 이용해 주셔서 감사합니다", true, 800);
  await channel.close();

  assert.equal(hub.ingestAttempts.length, 2, "한 번 더 보냈어야 한다");
  assert.equal(hub.ingested.length, 1);
  assert.equal(broadcaster.ofType("transcript").length, 1, "자막이 /ws 로 가야 한다");
  assert.equal(broadcaster.ofType("recommendation_pending").length, 1);
  assert.equal(hub.recommended.length, 1);
  assert.ok(log.warnings.some((line) => line.includes("call=test-1") && line.includes("segment=1") && line.includes("status=503")));
});

test("연결 실패·시간 초과(상태 없음)가 두 번 나도 세 번째에 보낸다", async () => {
  const { registry, hub, stt, broadcaster } = setup();
  const channel = await openOk(registry, "test-1", "customer");
  hub.ingestFailQueue.push(null, null);
  stt.last().emit("아 네 알겠습니다", true, 800);
  await channel.close();

  assert.equal(hub.ingestAttempts.length, 3);
  assert.equal(broadcaster.ofType("transcript").length, 1);
});

test("끝내 실패하면 정해진 횟수에서 멈추고, call_id·segment_id·시도 횟수만 경고한다 (원문 없음, SEC-1)", async () => {
  const { registry, hub, stt, broadcaster, log } = setup();
  const channel = await openOk(registry, "test-1", "customer");
  hub.failIngest = 503;
  stt.last().emit(RAW_PII, true, 800);
  await channel.close();

  assert.equal(hub.ingestAttempts.length, 3, "세 번(처음 + 재시도 둘)에서 멈춘다");
  assert.equal(broadcaster.messages.length, 0, "마스킹 안 된 결과는 어디에도 가지 않는다");
  const gaveUp = log.warnings.filter((line) => line.includes("전사 전달 포기"));
  assert.equal(gaveUp.length, 1);
  assert.ok(gaveUp[0]?.includes("call=test-1") && gaveUp[0]?.includes("segment=1") && gaveUp[0]?.includes("3회"));
  assert.ok(!log.warnings.join("\n").includes("900101"), "원문이 로그에 있다");
});

test("4xx(계약 위반·통화 없음)는 다시 보내도 같다 — 재시도하지 않는다", async () => {
  for (const status of [401, 409, 422]) {
    const { registry, hub, stt } = setup();
    const channel = await openOk(registry, "test-1", "agent");
    hub.failIngest = status;
    stt.last().emit("네", true, 800);
    await channel.close();
    assert.equal(hub.ingestAttempts.length, 1, `status ${status}`);
  }
});

test("interim 은 재시도하지 않는다 — 같은 발화의 새 결과가 곧 덮는다", async () => {
  const { registry, hub, stt } = setup();
  const channel = await openOk(registry, "test-1", "agent");
  hub.ingestFailQueue.push(503);
  stt.last().emit("네 이용해", false, 400);
  await channel.close();
  assert.equal(hub.ingestAttempts.length, 1);
  assert.equal(hub.ingested.length, 0);
});

test("재시도하는 동안 뒤 결과는 기다린다 — 자막 순서가 뒤집히지 않는다", async () => {
  const { registry, hub, stt, broadcaster } = setup({ ingestRetryDelaysMs: [30, 30] });
  const channel = await openOk(registry, "test-1", "agent");
  hub.ingestFailQueue.push(null);
  stt.last().emit("첫 확정", true, 800);
  stt.last().emit("둘째 확정", true, 1600);
  await channel.close();

  assert.deepEqual(
    broadcaster.ofType("transcript").map((m) => m.payload.segment_id),
    ["1", "2"],
  );
  assert.deepEqual(
    hub.ingestAttempts.map((raw) => raw.segment_id),
    [1, 1, 2],
  );
});
