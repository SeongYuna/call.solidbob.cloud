// Requirement: SEC-1, COST-1
import { test } from "node:test";
import assert from "node:assert/strict";
import { bearerToken, decideAccess, isLoopback } from "../src/domain/access.ts";

test("루프백은 IPv4·IPv6·IPv4 매핑 셋 다 알아본다", () => {
  assert.equal(isLoopback("127.0.0.1"), true);
  assert.equal(isLoopback("::1"), true);
  assert.equal(isLoopback("::ffff:127.0.0.1"), true);
  assert.equal(isLoopback("10.42.0.29"), false, "Traefik 에서 오는 파드 IP");
  assert.equal(isLoopback("::ffff:10.42.0.29"), false);
  assert.equal(isLoopback(undefined), false);
});

test("믿는 주소는 토큰 없이 받는다", () => {
  assert.deepEqual(decideAccess("", null, true), { ok: true });
});

test("fail-closed — 토큰이 설정되지 않았으면 바깥은 전부 거절한다", () => {
  assert.equal(decideAccess("", null, false).ok, false);
  assert.equal(decideAccess("", "아무거나", false).ok, false, "빈 토큰에 빈 값·아무 값이 맞아선 안 된다");
});

test("바깥은 토큰이 맞아야 한다 — 없거나 틀리면 거절", () => {
  const secret = "s3cret-token-with-enough-length";
  assert.equal(decideAccess(secret, null, false).ok, false);
  assert.equal(decideAccess(secret, "", false).ok, false);
  assert.equal(decideAccess(secret, "wrong", false).ok, false, "길이가 달라도 예외 없이 거절");
  assert.equal(decideAccess(secret, `${secret}x`, false).ok, false);
  assert.deepEqual(decideAccess(secret, secret, false), { ok: true });
});

test("Bearer 헤더에서 토큰만 뽑는다", () => {
  assert.equal(bearerToken("Bearer abc.def"), "abc.def");
  assert.equal(bearerToken("bearer abc"), "abc");
  assert.equal(bearerToken("Basic abc"), null);
  assert.equal(bearerToken(undefined), null);
  assert.equal(bearerToken("Bearer "), null);
});
