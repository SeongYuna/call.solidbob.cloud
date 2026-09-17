// Requirement: COST-1
import { test } from "node:test";
import assert from "node:assert/strict";
import { decideOpen, localDay, pcm16Seconds, remainingSeconds, usedInMonth } from "../src/domain/budget.ts";
import { BudgetGuard } from "../src/app/budget_guard.ts";
import { MemoryLedger, newLog } from "./fakes.ts";

const caps = { perDay: 600, perMonth: 3600 };
const day = "2026-09-11";

test("월 사용량은 같은 달의 날짜만 더한다", () => {
  const ledger = { "2026-08-31": 500, "2026-09-01": 100, "2026-09-11": 50 };
  assert.equal(usedInMonth(ledger, "2026-09"), 150);
});

test("남은 초는 일·월 중 더 빡빡한 쪽이다", () => {
  assert.equal(remainingSeconds({ [day]: 100 }, caps, day), 500);
  assert.equal(remainingSeconds({ "2026-09-01": 3400, [day]: 100 }, caps, day), 100);
  assert.equal(remainingSeconds({ [day]: 700 }, caps, day), 0);
});

test("캡이 비어 있으면 연다가 아니라 막는다 (fail-closed)", () => {
  const decision = decideOpen({}, { perDay: 0, perMonth: 3600 }, day);
  assert.equal(decision.ok, false);
});

test("일 한도를 다 쓰면 새 스트림을 열지 않는다", () => {
  const decision = decideOpen({ [day]: 600 }, caps, day);
  assert.equal(decision.ok, false);
  assert.match(decision.ok ? "" : decision.reason, /일 한도/);
});

test("PCM16 모노 바이트는 샘플레이트 × 2 가 1초다", () => {
  assert.equal(pcm16Seconds(32_000, 16_000), 1);
  assert.equal(pcm16Seconds(16_000, 8_000), 1);
});

test("localDay 는 로컬 시각 기준 YYYY-MM-DD", () => {
  assert.equal(localDay(new Date(2026, 8, 11, 23, 59)), "2026-09-11");
});

test("가드 — 열려 있는 스트림도 캡에 닿으면 거기서 끊는다", async () => {
  const store = new MemoryLedger({ [localDay(new Date())]: 598 });
  const guard = new BudgetGuard(store, caps, () => new Date(), newLog(), 1000);
  assert.equal((await guard.decideOpen()).ok, true);
  assert.equal(guard.consume(1.5), true);
  assert.equal(guard.consume(1.0), false, "598 + 1.5 + 1.0 > 600");
});

test("가드 — 메모리의 사용량을 장부에 쓴다", async () => {
  const store = new MemoryLedger();
  const guard = new BudgetGuard(store, caps, () => new Date(), newLog(), 1000);
  await guard.decideOpen();
  guard.consume(2);
  guard.consume(3);
  await guard.flush();
  assert.equal(store.ledger[localDay(new Date())], 5);
});

test("가드 — refresh() 뒤에는 채널을 열기 전에도 사용량을 보고한다", async () => {
  const store = new MemoryLedger({ [localDay(new Date())]: 5.6 });
  const guard = new BudgetGuard(store, caps, () => new Date(), newLog());
  assert.equal(guard.snapshot().usedTodaySeconds, 0, "읽기 전");
  await guard.refresh();
  assert.equal(guard.snapshot().usedTodaySeconds, 5.6);
});

test("가드 — 장부를 못 읽으면 막는다", async () => {
  const store = new MemoryLedger();
  store.failRead = true;
  const guard = new BudgetGuard(store, caps, () => new Date(), newLog());
  const decision = await guard.decideOpen();
  assert.equal(decision.ok, false);
});

test("가드 — 아직 장부에 안 쓴 사용량도 새 스트림 판정에 넣는다", async () => {
  const store = new MemoryLedger({ [localDay(new Date())]: 590 });
  const guard = new BudgetGuard(store, caps, () => new Date(), newLog(), 1000);
  await guard.decideOpen();
  assert.equal(guard.consume(9.5), true);
  const decision = await guard.decideOpen();
  assert.equal(decision.ok, false, "590 + 9.5(메모리) 면 1초도 안 남는다");
});

test("가드 — 장부에 못 쓰고 있으면 새 스트림을 막고, 쓰기가 돌아오면 다시 연다", async () => {
  const store = new MemoryLedger();
  const guard = new BudgetGuard(store, caps, () => new Date(), newLog(), 1000);
  assert.equal((await guard.decideOpen()).ok, true);
  guard.consume(3);
  store.failWrite = true;
  await guard.flush();
  const blocked = await guard.decideOpen();
  assert.equal(blocked.ok, false);
  assert.match(blocked.ok ? "" : blocked.reason, /쓰지 못하고/);
  assert.equal(guard.snapshot().usedTodaySeconds, 3, "못 쓴 초는 메모리에 남아 캡 계산에 들어간다");

  store.failWrite = false;
  assert.equal((await guard.decideOpen()).ok, true, "쓰기가 돌아오면 밀린 초를 쓰고 연다");
  assert.equal(store.ledger[localDay(new Date())], 3);
});
