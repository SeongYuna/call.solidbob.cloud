// Requirement: J-5
import { test } from "node:test";
import assert from "node:assert/strict";
import { loadConfig } from "../src/config.ts";

test("ROUTING_CANDIDATES — 쉼표로 가른 시연 상담원 ID, 없으면 빈 목록 (decisions/126)", () => {
  assert.deepEqual(loadConfig({ ROUTING_CANDIDATES: " agent-demo-1, ,agent-demo-2 " }).routingCandidates, ["agent-demo-1", "agent-demo-2"]);
  assert.deepEqual(loadConfig({}).routingCandidates, []);
});

test("F2_PROCEDURE_ADOPTION — 기본·모르는 값은 score-floor(2026-09-24 채택), 이름은 그대로 (decisions/219)", () => {
  assert.equal(loadConfig({}).procedureAdoption, "score-floor");
  assert.equal(loadConfig({ F2_PROCEDURE_ADOPTION: "sometimes" }).procedureAdoption, "score-floor");
  assert.equal(loadConfig({ F2_PROCEDURE_ADOPTION: " two-consecutive " }).procedureAdoption, "two-consecutive");
  assert.equal(loadConfig({ F2_PROCEDURE_ADOPTION: "top1" }).procedureAdoption, "top1");
});

test("CALL_GUARD_INTERVENTION_BETA — 정확히 1 일 때만 켜진다 (decisions/221)", () => {
  assert.equal(loadConfig({}).callGuardInterventionBeta, false);
  assert.equal(loadConfig({ CALL_GUARD_INTERVENTION_BETA: " 1 " }).callGuardInterventionBeta, true);
  assert.equal(loadConfig({ CALL_GUARD_INTERVENTION_BETA: "true" }).callGuardInterventionBeta, false);
});
