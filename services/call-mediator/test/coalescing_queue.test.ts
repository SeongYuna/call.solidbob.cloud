// Requirement: A-3
import { test } from "node:test";
import assert from "node:assert/strict";
import { CoalescingQueue } from "../src/app/coalescing_queue.ts";
import { tick } from "./fakes.ts";

interface Item {
  segmentId: number;
  isFinal: boolean;
  label: string;
}

function recorder(delayMs: number): { handled: string[]; queue: CoalescingQueue<Item> } {
  const handled: string[] = [];
  const queue = new CoalescingQueue<Item>(async (item) => {
    await tick(delayMs);
    handled.push(item.label);
  });
  return { handled, queue };
}

test("처리 중에 쌓인 같은 발화의 interim 은 가장 새 것만 보낸다", async () => {
  const { handled, queue } = recorder(5);
  queue.push({ segmentId: 1, isFinal: false, label: "i1" }); // 곧바로 처리 시작
  queue.push({ segmentId: 1, isFinal: false, label: "i2" });
  queue.push({ segmentId: 1, isFinal: false, label: "i3" });
  await queue.whenIdle();
  assert.deepEqual(handled, ["i1", "i3"]);
});

test("final 은 대기 중인 interim 을 대신하고, 그 자신은 갈아 끼워지지 않는다", async () => {
  const { handled, queue } = recorder(5);
  queue.push({ segmentId: 1, isFinal: false, label: "i1" });
  queue.push({ segmentId: 1, isFinal: false, label: "i2" });
  queue.push({ segmentId: 1, isFinal: true, label: "f1" });
  queue.push({ segmentId: 2, isFinal: false, label: "i-next" });
  queue.push({ segmentId: 2, isFinal: false, label: "i-next2" });
  await queue.whenIdle();
  assert.deepEqual(handled, ["i1", "f1", "i-next2"]);
});

test("final 끼리는 순서대로 전부 간다", async () => {
  const { handled, queue } = recorder(2);
  for (let id = 1; id <= 4; id += 1) {
    queue.push({ segmentId: id, isFinal: true, label: `f${id}` });
  }
  await queue.whenIdle();
  assert.deepEqual(handled, ["f1", "f2", "f3", "f4"]);
});

test("처리기 한 건이 실패해도 줄이 멈추지 않는다", async () => {
  const handled: number[] = [];
  const queue = new CoalescingQueue<Item>(async (item) => {
    if (item.segmentId === 1) {
      throw new Error("boom");
    }
    handled.push(item.segmentId);
  });
  queue.push({ segmentId: 1, isFinal: true, label: "" });
  queue.push({ segmentId: 2, isFinal: true, label: "" });
  await queue.whenIdle();
  assert.deepEqual(handled, [2]);
});
