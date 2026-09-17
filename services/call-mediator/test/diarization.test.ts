// Requirement: A-2
import { test } from "node:test";
import assert from "node:assert/strict";
import { FirstSpeakerIsAgent, newRuns, type TaggedWord } from "../src/domain/diarization.ts";

const w = (word: string, endMs: number, label: string | null): TaggedWord => ({ word, endMs, label });

test("같은 라벨이 이어지는 단어를 한 구간으로 묶고, 라벨이 바뀌면 자른다", () => {
  const runs = newRuns([w("네", 400, "1"), w("다산콜센터입니다", 1200, "1"), w("여권", 2100, "2"), w("재발급이요", 2600, "2")], 0);
  assert.deepEqual(runs, [
    { label: "1", text: "네 다산콜센터입니다", endMs: 1200 },
    { label: "2", text: "여권 재발급이요", endMs: 2600 },
  ]);
});

test("구글이 처음부터 다시 보낸 단어는 워터마크로 거른다", () => {
  const words = [w("네", 400, "1"), w("다산콜센터입니다", 1200, "1"), w("여권", 2100, "2")];
  assert.deepEqual(newRuns(words, 1200), [{ label: "2", text: "여권", endMs: 2100 }]);
  assert.deepEqual(newRuns(words, 2100), []);
});

test("라벨 없는 단어는 앞 구간에 붙이고, 앞이 없으면 버린다 — 누구 말인지 지어내지 않는다", () => {
  assert.deepEqual(newRuns([w("음", 100, null), w("네", 400, "1"), w("그", 500, null)], 0), [
    { label: "1", text: "네 그", endMs: 500 },
  ]);
});

test("먼저 말한 라벨이 상담원, 나머지는 전부 고객이다", () => {
  const speakers = new FirstSpeakerIsAgent();
  assert.equal(speakers.speakerOf("2"), "agent");
  assert.equal(speakers.speakerOf("1"), "customer");
  assert.equal(speakers.speakerOf("3"), "customer");
  assert.equal(speakers.speakerOf("2"), "agent");
});
