// Requirement: C-6
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  categoriesOf,
  nextIntervention,
  WARNING_ANNOUNCEMENT,
  FINAL_WARNING_ANNOUNCEMENT,
  INTERVENTION_PAUSE_MS,
} from "../src/domain/call_guard_intervention.ts";

test("첫 폭언 → warning, 일시정지, 「종료될 수 있다」 안내, 5.1", () => {
  const it = nextIntervention(0, ["insult"])!;
  assert.equal(it.stage, "warning");
  assert.equal(it.abuseCount, 1);
  assert.equal(it.pauseMs, INTERVENTION_PAUSE_MS);
  assert.equal(it.announcement, WARNING_ANNOUNCEMENT);
  assert.ok(it.announcement!.includes("종료될 수 있습니다"));
  assert.equal(it.sourceDocId, "DASAN-MANUAL-5.1");
});

test("두 번째 insult → final_warning", () => {
  const it = nextIntervention(1, ["insult"])!;
  assert.equal(it.stage, "final_warning");
  assert.equal(it.announcement, FINAL_WARNING_ANNOUNCEMENT);
  assert.equal(it.abuseCount, 2);
});

test("세 번째 이상 → end_suggested, 일시정지·안내 없음, 5.2", () => {
  for (const before of [2, 5]) {
    const it = nextIntervention(before, ["insult"])!;
    assert.equal(it.stage, "end_suggested");
    assert.equal(it.pauseMs, 0);
    assert.equal(it.announcement, null);
    assert.equal(it.sourceDocId, "DASAN-MANUAL-5.2");
  }
});

test("1차 안내 뒤 threat·sexual → 곧바로 end_suggested (5.2)", () => {
  assert.equal(nextIntervention(1, ["threat"])!.stage, "end_suggested");
  assert.equal(nextIntervention(1, ["sexual", "insult"])!.stage, "end_suggested");
});

test("첫 발화가 threat 이어도 먼저 1차 안내", () => {
  assert.equal(nextIntervention(0, ["threat"])!.stage, "warning");
});

test("distress only → null (5.4 — 폭언과 다르게 다룬다)", () => {
  assert.equal(nextIntervention(0, ["distress"]), null);
  assert.equal(nextIntervention(3, []), null);
});

test("갈래가 여럿이어도 발화당 1회", () => {
  assert.equal(nextIntervention(0, ["insult", "threat", "insult"])!.abuseCount, 1);
});

test("categoriesOf — 객체가 아니거나 category 가 없거나 문자열이 아니면 건너뛴다", () => {
  assert.deepEqual(
    categoriesOf([
      { category: "insult" },
      null,
      "x",
      { phrase: "a" },
      { category: 3 },
      { category: "distress" },
    ]),
    ["insult", "distress"],
  );
});

test("문구에 금지 표현이 없다 (부록 A-1)", () => {
  for (const text of [WARNING_ANNOUNCEMENT, FINAL_WARNING_ANNOUNCEMENT]) {
    for (const bad of ["위험", "%", "점수", "확실"]) assert.ok(!text.includes(bad));
  }
});
