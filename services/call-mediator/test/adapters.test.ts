// Requirement: COST-1, SEC-1, 7.3절
import { test } from "node:test";
import assert from "node:assert/strict";
import { createServer, type IncomingMessage } from "node:http";
import type { AddressInfo } from "node:net";
import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { HttpHub } from "../src/adapters/hub_http.ts";
import { JsonLedgerFile } from "../src/adapters/ledger_file.ts";
import { HubError } from "../src/app/ports.ts";

async function body(req: IncomingMessage): Promise<unknown> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(chunk as Buffer);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf-8"));
}

test("HttpHub — 서버 계약 경로로 JSON 을 보낸다", async () => {
  const seen: Array<{ path: string; payload: unknown }> = [];
  const server = createServer(async (req, res) => {
    seen.push({ path: req.url ?? "", payload: await body(req) });
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(req.url === "/hub/transcripts" ? { text: "가림" } : { fired: "false" }));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const hub = new HttpHub(`http://127.0.0.1:${(server.address() as AddressInfo).port}/`);
  try {
    await hub.startCall({ call_id: "test-1", stt_engine: "google-stt", channel_count: 1 });
    const masked = await hub.ingestTranscript({
      call_id: "test-1",
      segment_id: 1,
      speaker: "agent",
      text: "원문",
      is_final: true,
      utterance_end_ms: 10,
    });
    assert.equal(masked.text, "가림");
    assert.deepEqual(
      seen.map((item) => item.path),
      ["/hub/calls", "/hub/transcripts"],
    );
  } finally {
    server.close();
  }
});

test("HttpHub — 실패는 상태 코드만 담는다 (422 본문에는 원문이 되돌아온다)", async () => {
  const server = createServer((_req, res) => {
    res.writeHead(422, { "content-type": "application/json" });
    res.end(JSON.stringify({ detail: [{ input: "주민번호 900101-1234567" }] }));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const hub = new HttpHub(`http://127.0.0.1:${(server.address() as AddressInfo).port}`);
  try {
    await assert.rejects(
      hub.ingestTranscript({ call_id: "c", segment_id: 1, speaker: "agent", text: "x", is_final: true, utterance_end_ms: 0 }),
      (error: unknown) => {
        assert.ok(error instanceof HubError);
        assert.equal(error.status, 422);
        assert.ok(!error.message.includes("900101"));
        return true;
      },
    );
  } finally {
    server.close();
  }
});

test("HttpHub — 서버가 없으면 status=null", async () => {
  const hub = new HttpHub("http://127.0.0.1:9", 500);
  await assert.rejects(hub.startCall({ call_id: "c", stt_engine: "x", channel_count: 1 }), (error: unknown) => {
    assert.ok(error instanceof HubError);
    assert.equal(error.status, null);
    return true;
  });
});

test("장부 파일 — 배치 스크립트가 쓴 값을 덮지 않고 더한다", async () => {
  const dir = await mkdtemp(join(tmpdir(), "ledger-"));
  const path = join(dir, "stt-usage.json");
  // transcribe_batch.py 가 쓰는 모양 (json.dumps(indent=2, sort_keys=True))
  await writeFile(path, JSON.stringify({ "2026-09-10": 120.5, "2026-09-11": 30 }, null, 2));
  const store = new JsonLedgerFile(path);
  const after = await store.add("2026-09-11", 12);
  assert.deepEqual(after, { "2026-09-10": 120.5, "2026-09-11": 42 });
  assert.deepEqual(JSON.parse(await readFile(path, "utf-8")), after);
});

test("장부 파일 — 없으면 빈 장부, 깨졌으면 예외", async () => {
  const dir = await mkdtemp(join(tmpdir(), "ledger-"));
  assert.deepEqual(await new JsonLedgerFile(join(dir, "none.json")).read(), {});
  const broken = join(dir, "broken.json");
  await writeFile(broken, "{not json");
  await assert.rejects(new JsonLedgerFile(broken).read());
});

test("HttpHub — 콜 가드 검사는 /hub/call-guard-checks 로 보내고, flags 배열이 없으면 계약 위반이다", async () => {
  const seen: Array<{ path: string; payload: unknown }> = [];
  let reply: unknown = { call_id: "test-1", segment_id: "2", flags: [] };
  const server = createServer(async (req, res) => {
    seen.push({ path: req.url ?? "", payload: await body(req) });
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(reply));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const hub = new HttpHub(`http://127.0.0.1:${(server.address() as AddressInfo).port}`);
  const request = { call_id: "test-1", segment_id: 2, customer_utterance: "마스킹된 발화" };
  try {
    const payload = await hub.checkCallGuard(request);
    assert.deepEqual(payload.flags, []);
    assert.deepEqual(seen, [{ path: "/hub/call-guard-checks", payload: request }]);
    reply = { call_id: "test-1" };
    await assert.rejects(hub.checkCallGuard(request), HubError);
  } finally {
    server.close();
  }
});

test("HttpHub — 컴플라이언스 검사는 /hub/compliance-checks 로 보내고, findings 배열이 없으면 계약 위반이다", async () => {
  const seen: Array<{ path: string; payload: unknown }> = [];
  let reply: unknown = { call_id: "test-1", segment_id: "2", findings: [] };
  const server = createServer(async (req, res) => {
    seen.push({ path: req.url ?? "", payload: await body(req) });
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(reply));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const hub = new HttpHub(`http://127.0.0.1:${(server.address() as AddressInfo).port}`);
  const request = { call_id: "test-1", segment_id: 2, agent_utterance: "마스킹된 상담원 발화" };
  try {
    const payload = await hub.checkCompliance(request);
    assert.deepEqual(payload.findings, []);
    assert.deepEqual(seen, [{ path: "/hub/compliance-checks", payload: request }]);
    reply = { call_id: "test-1" };
    await assert.rejects(hub.checkCompliance(request), HubError);
  } finally {
    server.close();
  }
});

test("HttpHub — 필요서류 판정은 /hub/required-docs-checks 로 보내고, procedure 가 없으면 계약 위반이다", async () => {
  const seen: Array<{ path: string; payload: unknown }> = [];
  let reply: unknown = { call_id: "test-1", procedure: "DASAN-TERM-4.3", verdict: "incomplete" };
  const server = createServer(async (req, res) => {
    seen.push({ path: req.url ?? "", payload: await body(req) });
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(reply));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const hub = new HttpHub(`http://127.0.0.1:${(server.address() as AddressInfo).port}`);
  const request = { call_id: "test-1", procedure: "DASAN-TERM-4.3", agent_utterances: ["신분증 가져오세요"] };
  try {
    assert.equal((await hub.checkRequiredDocs(request)).procedure, "DASAN-TERM-4.3");
    assert.deepEqual(seen, [{ path: "/hub/required-docs-checks", payload: request }]);
    reply = { call_id: "test-1" };
    await assert.rejects(hub.checkRequiredDocs(request), HubError);
  } finally {
    server.close();
  }
});

test("HttpHub — 서비스 토큰이 있으면 Authorization 으로 보낸다 (decisions/120)", async () => {
  // 2026-09-20 운영 왕복에서 server 의 쓰기 경로가 토큰 없이 200 이었다. server 가 문을 달았고(`INGEST_SERVICE_TOKEN`),
  // 미디에이터는 같은 값을 헤더로 보낸다. 부르는 경로 **전부**에 실려야 한다 — 하나라도 빠지면 그 경로만 401 이 된다.
  const seen: Array<{ path: string; auth: string | undefined }> = [];
  const server = createServer(async (req, res) => {
    await body(req);
    seen.push({ path: req.url ?? "", auth: req.headers.authorization });
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(req.url === "/hub/transcripts" ? { text: "가림" } : { fired: "false", flags: [], findings: [] }));
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const hub = new HttpHub(`http://127.0.0.1:${(server.address() as AddressInfo).port}`, 5_000, "svc-token-abc");
  try {
    await hub.startCall({ call_id: "test-1", stt_engine: "google-stt", channel_count: 1 });
    await hub.ingestTranscript({ call_id: "test-1", segment_id: 1, speaker: "agent", text: "원문", is_final: true, utterance_end_ms: 10 });
    await hub.checkCallGuard({ call_id: "test-1", segment_id: 1, customer_utterance: "가림" });
    await hub.checkCompliance({ call_id: "test-1", segment_id: 1, agent_utterance: "가림" });
    await hub.decideRouting({ call_id: "test-1", candidates: [] }); // decisions/126 — 같은 문을 지난다
  } finally {
    server.close();
  }
  assert.equal(seen.length, 5);
  assert.ok(seen.some((hit) => hit.path === "/hub/routing-decisions"));
  for (const hit of seen) {
    assert.equal(hit.auth, "Bearer svc-token-abc", `${hit.path} 에 토큰이 안 실렸다`);
  }
});

test("HttpHub — 서비스 토큰이 없으면 Authorization 을 보내지 않는다 (이행기)", async () => {
  // server 가 아직 토큰을 요구하지 않는 동안에도 같은 코드로 돈다. 빈 `Bearer ` 를 보내면 server 가 401 로 읽는다.
  let auth: string | undefined = "unset";
  const server = createServer(async (req, res) => {
    await body(req);
    auth = req.headers.authorization;
    res.writeHead(200, { "content-type": "application/json" });
    res.end("{}");
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const hub = new HttpHub(`http://127.0.0.1:${(server.address() as AddressInfo).port}`);
  try {
    await hub.startCall({ call_id: "test-1", stt_engine: "google-stt", channel_count: 1 });
  } finally {
    server.close();
  }
  assert.equal(auth, undefined);
});
