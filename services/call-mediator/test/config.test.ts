// Requirement: J-5
import { test } from "node:test";
import assert from "node:assert/strict";
import { loadConfig } from "../src/config.ts";

test("ROUTING_CANDIDATES — 쉼표로 가른 시연 상담원 ID, 없으면 빈 목록 (decisions/126)", () => {
  assert.deepEqual(loadConfig({ ROUTING_CANDIDATES: " agent-demo-1, ,agent-demo-2 " }).routingCandidates, ["agent-demo-1", "agent-demo-2"]);
  assert.deepEqual(loadConfig({}).routingCandidates, []);
});
