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
