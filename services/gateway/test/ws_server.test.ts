// Requirement: A-3, SEC-1, 7.3절
/**
 * 진짜 소켓을 연다 — 생산자(/ingest) → 게이트웨이 → 대시보드(/ws). STT·서버만 가짜다.
 * 대시보드 쪽 검증은 `apps/dashboard/src/lib/ws/realGatewayClient.ts` 의 `parseGatewayMessage`
 * 가 요구하는 것 그대로다 — `{type, payload}`, 말단 값은 전부 문자열.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import type { AddressInfo } from "node:net";
import { WebSocket } from "ws";
import { BudgetGuard } from "../src/app/budget_guard.ts";
import { CallRegistry } from "../src/app/call_registry.ts";
import { DashboardHub, createGatewayServer } from "../src/adapters/ws_server.ts";
import { allLeavesStringOrNull, FakeHub, FakeStt, MemoryLedger, newLog, silence, tick } from "./fakes.ts";

async function startGateway(
  opts: {
    caps?: { perDay: number; perMonth: number };
    tokens?: { ingest: string; view: string };
    trustLoopback?: boolean;
    heartbeatMs?: number;
  } = {},
) {
  const hub = new FakeHub();
  const stt = new FakeStt();
  const log = newLog();
  const dashboards = new DashboardHub();
  const budget = new BudgetGuard(new MemoryLedger(), opts.caps ?? { perDay: 600, perMonth: 3600 }, () => new Date(), log, 1000);
  const registry = new CallRegistry({ hub, stt, budget, broadcaster: dashboards, log, nowMs: () => Date.now(), drainTimeoutMs: 500 });
  const server = createGatewayServer({
    registry,
    dashboards,
    allowedOrigins: ["http://localhost:5173"],
    tokens: opts.tokens ?? { ingest: "", view: "" },
    isTrustedAddress: opts.trustLoopback === false ? () => false : undefined,
    heartbeatMs: opts.heartbeatMs,
    log,
    health: () => ({ status: "ok", active_calls: registry.activeCalls }),
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = (server.address() as AddressInfo).port;
  return {
    hub,
    stt,
    dashboards,
    log,
    base: `127.0.0.1:${port}`,
    close: () => new Promise<void>((resolve) => server.close(() => resolve())),
  };
}

function connect(url: string, headers: Record<string, string> = {}): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url, { headers });
    ws.once("open", () => resolve(ws));
    ws.once("error", reject);
  });
}

function nextClose(ws: WebSocket): Promise<{ code: number; reason: string }> {
  return new Promise((resolve) => ws.once("close", (code, reason) => resolve({ code, reason: reason.toString() })));
}

async function waitFor(predicate: () => boolean, ms = 1000): Promise<void> {
  const until = Date.now() + ms;
  while (!predicate()) {
    if (Date.now() > until) {
      throw new Error("시간 초과");
    }
    await tick(5);
  }
}

test("생산자 오디오 → STT → 서버 → 대시보드: 대시보드 파서가 받는 형식 그대로다", async () => {
  const gw = await startGateway();
  try {
    const dashboard = await connect(`ws://${gw.base}/ws`, { origin: "http://localhost:5173" });
    const received: unknown[] = [];
    dashboard.on("message", (data) => received.push(JSON.parse(data.toString())));
    await waitFor(() => gw.dashboards.size === 1);

    const producer = await connect(`ws://${gw.base}/ingest?call_id=test-ws-1&speaker=customer&sample_rate=16000`);
    producer.send(silence(0.2));
    await waitFor(() => gw.stt.streams.length === 1);
    await waitFor(() => gw.stt.last().bytes > 0);

    gw.stt.last().emit("전화번호는 010-1234-5678", true, 1500);
    await waitFor(() => received.length >= 2);

    const transcript = received.find((m) => (m as { type: string }).type === "transcript") as {
      type: string;
      payload: Record<string, unknown>;
    };
    assert.ok(transcript, "전사 메시지가 없다");
    for (const key of ["call_id", "segment_id", "speaker", "text", "masked", "is_final", "utterance_end_ms"]) {
      assert.ok(key in transcript.payload, `${key} 가 없다 — 대시보드가 이 이벤트를 버린다`);
    }
    assert.ok(allLeavesStringOrNull(transcript.payload), "문자열 아닌 값이 있다 — 대시보드가 alert 를 띄운다");
    assert.equal(transcript.payload["text"], "전화번호는 ***-****-****");
    assert.ok(!JSON.stringify(received).includes("1234"), "원문이 대시보드로 갔다");

    const recommendation = received.find((m) => (m as { type: string }).type === "recommendation") as {
      payload: Record<string, unknown>;
    };
    assert.equal(recommendation.payload["fired"], "true");

    const closed = nextClose(producer);
    producer.send(JSON.stringify({ type: "end" }));
    assert.equal((await closed).code, 1000);
    dashboard.close();
  } finally {
    await gw.close();
  }
});

test("call_id 로 구독하면 그 통화만 받는다", async () => {
  const gw = await startGateway();
  try {
    const onlyA = await connect(`ws://${gw.base}/ws?call_id=test-a`);
    const got: string[] = [];
    onlyA.on("message", (data) => got.push(JSON.parse(data.toString()).payload.call_id));
    await waitFor(() => gw.dashboards.size === 1);

    const a = await connect(`ws://${gw.base}/ingest?call_id=test-a&speaker=agent`);
    const b = await connect(`ws://${gw.base}/ingest?call_id=test-b&speaker=agent`);
    await waitFor(() => gw.stt.streams.length === 2);
    gw.stt.streams[0]!.emit("가", false, 100);
    gw.stt.streams[1]!.emit("나", false, 100);
    await waitFor(() => gw.hub.ingested.length === 2);
    await tick(20);
    assert.deepEqual(got, ["test-a"]);
    a.close();
    b.close();
    onlyA.close();
  } finally {
    await gw.close();
  }
});

test("허용되지 않은 Origin 은 연결 자체를 거절한다", async () => {
  const gw = await startGateway();
  try {
    await assert.rejects(connect(`ws://${gw.base}/ws`, { origin: "https://evil.example" }));
  } finally {
    await gw.close();
  }
});

test("잘못된 파라미터는 1008 과 이유로 닫는다", async () => {
  const gw = await startGateway();
  try {
    const ws = await connect(`ws://${gw.base}/ingest?call_id=test-1&speaker=robot`);
    const closed = await nextClose(ws);
    assert.equal(closed.code, 1008);
    assert.match(closed.reason, /speaker/);
  } finally {
    await gw.close();
  }
});

test("캡이 없으면 1013 으로 닫는다 — 구글에 한 바이트도 가지 않는다", async () => {
  const gw = await startGateway({ caps: { perDay: 0, perMonth: 0 } });
  try {
    const ws = await connect(`ws://${gw.base}/ingest?call_id=test-1&speaker=agent`);
    ws.send(silence(0.1));
    const closed = await nextClose(ws);
    assert.equal(closed.code, 1013);
    assert.equal(gw.stt.streams.length, 0);
    assert.equal(gw.hub.calls.length, 0);
  } finally {
    await gw.close();
  }
});

test("채널이 열리기 전에 온 오디오도 버리지 않는다", async () => {
  const gw = await startGateway();
  gw.hub.ingestDelayMs = 0;
  try {
    const ws = await connect(`ws://${gw.base}/ingest?call_id=test-early&speaker=agent`);
    ws.send(silence(0.1));
    ws.send(silence(0.1));
    await waitFor(() => gw.stt.streams.length === 1 && gw.stt.last().bytes === silence(0.2).byteLength);
    ws.close();
  } finally {
    await gw.close();
  }
});

// ── 접속 제어 — 바깥 클라이언트를 흉내 낸다(isTrustedAddress = 전부 거짓) ──

const INGEST = "ingest-secret-0123456789abcdef";
const VIEW = "view-token-not-secret";

function upgradeStatus(url: string, headers: Record<string, string> = {}): Promise<number | "open"> {
  return new Promise((resolve) => {
    const ws = new WebSocket(url, { headers });
    ws.once("open", () => {
      ws.close();
      resolve("open");
    });
    ws.once("unexpected-response", (_req, res) => resolve(res.statusCode ?? 0));
    ws.once("error", () => {});
  });
}

test("fail-closed — 토큰을 안 넣고 밖에 열면 두 문 다 401", async () => {
  const gw = await startGateway({ trustLoopback: false });
  try {
    assert.equal(await upgradeStatus(`ws://${gw.base}/ws`), 401);
    assert.equal(await upgradeStatus(`ws://${gw.base}/ingest?call_id=test-1&speaker=agent`), 401);
    assert.equal(gw.hub.calls.length, 0, "거절된 접속이 통화를 열었다");
  } finally {
    await gw.close();
  }
});

test("/ingest — 맞는 토큰을 헤더로 내면 받는다. 없거나 틀리면 401", async () => {
  const gw = await startGateway({ trustLoopback: false, tokens: { ingest: INGEST, view: VIEW } });
  const url = `ws://${gw.base}/ingest?call_id=test-auth&speaker=agent`;
  try {
    assert.equal(await upgradeStatus(url), 401);
    assert.equal(await upgradeStatus(url, { authorization: "Bearer wrong" }), 401);
    assert.equal(await upgradeStatus(url, { authorization: `Bearer ${INGEST}` }), "open");
  } finally {
    await gw.close();
  }
});

test("/ingest 비밀은 URL 로 받지 않는다 — 접근 로그에 남는다", async () => {
  const gw = await startGateway({ trustLoopback: false, tokens: { ingest: INGEST, view: VIEW } });
  try {
    assert.equal(await upgradeStatus(`ws://${gw.base}/ingest?call_id=test-q&speaker=agent&token=${INGEST}`), 401);
  } finally {
    await gw.close();
  }
});

test("토큰은 문마다 따로다 — 대시보드 토큰으로 과금 문이 열리지 않는다", async () => {
  const gw = await startGateway({ trustLoopback: false, tokens: { ingest: INGEST, view: VIEW } });
  try {
    assert.equal(await upgradeStatus(`ws://${gw.base}/ingest?call_id=test-x&speaker=agent`, { authorization: `Bearer ${VIEW}` }), 401);
    assert.equal(await upgradeStatus(`ws://${gw.base}/ws`, { authorization: `Bearer ${INGEST}` }), 401);
  } finally {
    await gw.close();
  }
});

test("/ws — 브라우저처럼 ?token= 으로 내도 받는다", async () => {
  const gw = await startGateway({ trustLoopback: false, tokens: { ingest: INGEST, view: VIEW } });
  try {
    assert.equal(await upgradeStatus(`ws://${gw.base}/ws`), 401);
    assert.equal(await upgradeStatus(`ws://${gw.base}/ws?token=nope`), 401);
    assert.equal(await upgradeStatus(`ws://${gw.base}/ws?token=${VIEW}`), "open");
  } finally {
    await gw.close();
  }
});

test("거절 로그에 토큰이 남지 않는다 — 어느 문·왜만 남는다", async () => {
  const gw = await startGateway({ trustLoopback: false, tokens: { ingest: INGEST, view: VIEW } });
  try {
    await upgradeStatus(`ws://${gw.base}/ws?token=leaky-guess`);
    await upgradeStatus(`ws://${gw.base}/ingest?call_id=test-l&speaker=agent`, { authorization: "Bearer leaky-bearer" });
    const logged = gw.log.warnings.join("\n");
    assert.match(logged, /접속 거절 \/ws — 토큰이 맞지 않다/);
    assert.match(logged, /접속 거절 \/ingest — 토큰이 맞지 않다/);
    assert.ok(!logged.includes("leaky"), "내민 토큰이 로그에 남았다");
  } finally {
    await gw.close();
  }
});

test("GET /health 는 토큰 없이도 된다 — 쿠버네티스 프로브", async () => {
  const gw = await startGateway({ trustLoopback: false, tokens: { ingest: INGEST, view: VIEW } });
  try {
    assert.equal((await fetch(`http://${gw.base}/health`)).status, 200);
  } finally {
    await gw.close();
  }
});

test("GET /health", async () => {
  const gw = await startGateway();
  try {
    const response = await fetch(`http://${gw.base}/health`);
    assert.equal(response.status, 200);
    assert.equal((await response.json()).status, "ok");
  } finally {
    await gw.close();
  }
});

// ── 운영 경로 (/gateway) · 연결 유지 ──

test("운영 Ingress 경로 /gateway 로 와도 같은 문이다 — /gateway/ws · /gateway/health", async () => {
  const gw = await startGateway({ trustLoopback: false, tokens: { ingest: INGEST, view: VIEW } });
  try {
    assert.equal(await upgradeStatus(`ws://${gw.base}/gateway/ws?token=${VIEW}`), "open");
    assert.equal(await upgradeStatus(`ws://${gw.base}/gateway/ws`), 401, "접두어가 붙어도 토큰 검사는 같다");
    assert.equal(await upgradeStatus(`ws://${gw.base}/gateway/ingest?call_id=test-p&speaker=agent`, { authorization: `Bearer ${INGEST}` }), "open");
    assert.equal((await fetch(`http://${gw.base}/gateway/health`)).status, 200);
  } finally {
    await gw.close();
  }
});

test("접두어 비슷한 경로는 따로 치지 않는다 — /gatewayx/ws 는 404", async () => {
  const gw = await startGateway();
  try {
    assert.equal(await upgradeStatus(`ws://${gw.base}/gatewayx/ws`), 404);
  } finally {
    await gw.close();
  }
});

test("대기 중인 연결에 ping 을 보낸다 — 프록시가 조용한 연결을 끊지 않게", async () => {
  const gw = await startGateway({ heartbeatMs: 30 });
  try {
    const ws = await connect(`ws://${gw.base}/ws`);
    let pings = 0;
    ws.on("ping", () => {
      pings += 1;
    });
    await waitFor(() => pings >= 2, 1000);
    assert.equal(ws.readyState, ws.OPEN, "pong 을 돌려주는 클라이언트는 끊지 않는다");
    ws.close();
  } finally {
    await gw.close();
  }
});
