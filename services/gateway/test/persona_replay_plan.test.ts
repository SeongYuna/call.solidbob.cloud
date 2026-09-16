// Requirement: A-1, A-3
import assert from "node:assert/strict";
import { test } from "node:test";
import { gapBefore, planTurn, readTurns, sayRate, type ScriptTurn } from "../scripts/persona_replay/plan.ts";

const turn = (text: string, tone: ScriptTurn["tone"] = "calm", speaker: ScriptTurn["speaker"] = "customer"): ScriptTurn => ({
  seq: 1,
  speaker,
  text,
  tone,
});

test("부분 결과는 앞에서부터 어절째 늘어나고, 전체 글자는 확정에만 간다", () => {
  const plan = planTurn(turn("아동수당 신청하려면 뭐가 필요해요 서류 알려 주세요"));
  assert.deepEqual(
    plan.interims.map((i) => i.text),
    ["아동수당 신청하려면", "아동수당 신청하려면 뭐가 필요해요", "아동수당 신청하려면 뭐가 필요해요 서류 알려"],
  );
  const offsets = plan.interims.map((i) => i.offsetMs);
  assert.deepEqual(offsets, [...offsets].sort((a, b) => a - b), "시각이 거꾸로 간다");
  assert.ok(offsets.every((ms) => ms > 0 && ms < plan.durationMs), "부분 결과가 확정 뒤에 온다");
});

test("짧은 턴은 부분 결과 없이 확정 하나, 최소 길이는 지킨다", () => {
  const plan = planTurn(turn("네."));
  assert.deepEqual(plan.interims, []);
  assert.equal(plan.durationMs, 700);
});

test("톤이 오르면 빨리, 가라앉으면 느리게 말한다 — speed 로 전체를 줄인다", () => {
  const text = "그러니까 그걸 왜 내가 다 내야 되냐고요";
  const calm = planTurn(turn(text, "calm")).durationMs;
  assert.ok(planTurn(turn(text, "shouting")).durationMs < calm);
  assert.ok(planTurn(turn(text, "weary")).durationMs > calm);
  assert.equal(planTurn(turn(text, "calm"), 2).durationMs, Math.round(calm / 2));
  assert.ok(sayRate("shouting") > sayRate("calm") && sayRate("weary") < sayRate("calm"));
  assert.throws(() => planTurn(turn(text), 0), /speed/);
});

test("화자가 바뀌면 더 쉬고, 첫 턴은 바로 시작한다", () => {
  const a = turn("안녕하세요", "calm", "agent");
  const c = turn("네", "calm", "customer");
  assert.equal(gapBefore(undefined, a), 0);
  assert.ok(gapBefore(a, c) > gapBefore(c, c));
});

test("대본 형식이 틀리면 어느 턴인지 밝힌다 · 모르는 톤은 calm", () => {
  assert.throws(() => readTurns({}), /turns/);
  assert.throws(() => readTurns({ turns: [{ speaker: "bot", text: "x" }] }), /turns\[0\]\.speaker/);
  assert.throws(() => readTurns({ turns: [{ speaker: "agent", text: " " }] }), /turns\[0\]\.text/);
  assert.equal(readTurns({ turns: [{ speaker: "agent", text: "네", tone: "angry" }] })[0]?.tone, "calm");
});
