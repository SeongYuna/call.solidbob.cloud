// Requirement: F-3
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseArgs } from "../scripts/replay_persona_call.ts";

test("--ring-seconds 기본은 0 — 지금 동작 그대로", () => {
  assert.equal(parseArgs(["SYN-004"]).ringMs, 0);
});

test("--ring-seconds 12 → 12000ms", () => {
  assert.equal(parseArgs(["SYN-004", "--ring-seconds", "12"]).ringMs, 12_000);
});

test("--ring-seconds 음수·숫자 아님은 거절", () => {
  assert.throws(() => parseArgs(["SYN-004", "--ring-seconds", "-1"]));
  assert.throws(() => parseArgs(["SYN-004", "--ring-seconds", "abc"]));
});
