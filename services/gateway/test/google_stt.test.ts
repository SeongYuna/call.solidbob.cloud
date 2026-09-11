// Requirement: A-1, A-4
/** 구글 없이 교대 로직만 본다 — 스트림 가짜를 공장에 꽂는다. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { GoogleSttEngine, type RecognizeStream } from "../src/adapters/google_stt.ts";
import type { SttResult } from "../src/app/ports.ts";
import { silence } from "./fakes.ts";

class FakeRecognizeStream extends EventEmitter implements RecognizeStream {
  bytes = 0;
  ended = false;

  write(chunk: Buffer): boolean {
    this.bytes += chunk.byteLength;
    return true;
  }

  end(): void {
    this.ended = true;
  }

  result(text: string, isFinal: boolean, endSeconds: number): void {
    this.emit("data", {
      results: [
        {
          isFinal,
          alternatives: [{ transcript: text }],
          resultEndTime: { seconds: String(Math.floor(endSeconds)), nanos: Math.round((endSeconds % 1) * 1e9) },
        },
      ],
    });
  }

  close(): void {
    this.emit("end");
  }
}

function setup(rotateAfterMs: number, hardLimitMs: number) {
  const streams: FakeRecognizeStream[] = [];
  const engine = new GoogleSttEngine(
    () => {
      const stream = new FakeRecognizeStream();
      streams.push(stream);
      return stream;
    },
    { rotateAfterMs, hardLimitMs },
  );
  const results: SttResult[] = [];
  const fatals: string[] = [];
  let ended = false;
  const stt = engine.open(16000, {
    onResult: (result) => results.push(result),
    onFatal: (message) => fatals.push(message),
    onEnd: () => {
      ended = true;
    },
  });
  return { streams, results, fatals, stt, isEnded: () => ended };
}

test("첫 오디오가 올 때 스트림을 연다", () => {
  const { streams, stt } = setup(60_000, 120_000);
  assert.equal(streams.length, 0);
  stt.write(silence(0.1));
  assert.equal(streams.length, 1);
});

test("rotateAfterMs 를 넘긴 뒤 final 이 오면 새 스트림으로 갈아타고, 시각을 이어 붙인다", () => {
  const { streams, results, stt } = setup(2_000, 10_000);
  stt.write(silence(3)); // 3초 — 교대 기준(2초) 넘김
  streams[0]!.result("첫 문장", true, 2.5);
  assert.equal(streams[0]!.ended, true, "final 뒤 옛 스트림을 닫지 않았다");

  stt.write(silence(1));
  assert.equal(streams.length, 2);
  streams[1]!.result("둘째 문장", true, 0.8);
  assert.equal(results[1]?.audioEndMs, 3_000 + 800, "새 스트림 결과 시각에 앞서 보낸 3초를 더해야 한다");
});

test("hardLimitMs 를 넘기면 final 을 기다리지 않고 갈아탄다", () => {
  const { streams, stt } = setup(60_000, 2_000);
  stt.write(silence(2));
  stt.write(silence(0.5));
  assert.equal(streams.length, 2);
  assert.equal(streams[0]!.ended, true);
});

test("옛 스트림이 교대 뒤에 보낸 결과는 옛 기준 시각으로 붙는다", () => {
  const { streams, results, stt } = setup(60_000, 2_000);
  stt.write(silence(2));
  stt.write(silence(1)); // 교대 — 두 번째 스트림 base = 2초
  streams[0]!.result("끝나가던 말", true, 1.9);
  assert.equal(results[0]?.audioEndMs, 1_900);
});

test("응답 하나의 interim 조각들은 이어 붙여 한 결과로 낸다 (2026-09-11 실측 모양)", () => {
  const { streams, results, stt } = setup(600_000, 600_000);
  stt.write(silence(1));
  streams[0]!.emit("data", {
    results: [
      { isFinal: false, alternatives: [{ transcript: "로미 기프트콘" }], resultEndTime: { seconds: "1", nanos: 0 } },
      { isFinal: false, alternatives: [{ transcript: " 쓰고 다른" }], resultEndTime: { seconds: "1", nanos: 500_000_000 } },
    ],
  });
  assert.equal(results.length, 1, "조각마다 따로 내면 같은 번호로 서로 덮어쓴다");
  assert.equal(results[0]?.text, "로미 기프트콘 쓰고 다른");
  assert.equal(results[0]?.audioEndMs, 1_500);
});

test("final 과 다음 발화의 interim 이 한 응답에 오면 둘로 나눈다", () => {
  const { streams, results, stt } = setup(600_000, 600_000);
  stt.write(silence(1));
  streams[0]!.emit("data", {
    results: [
      { isFinal: true, alternatives: [{ transcript: "주문할게요" }], resultEndTime: { seconds: "2" } },
      { isFinal: false, alternatives: [{ transcript: "그리고" }], resultEndTime: { seconds: "3" } },
    ],
  });
  assert.deepEqual(
    results.map((r) => [r.text, r.isFinal]),
    [
      ["주문할게요", true],
      ["그리고", false],
    ],
  );
});

test("25KB 넘는 오디오는 잘라서 보낸다", () => {
  const { streams, stt } = setup(600_000, 600_000);
  const big = silence(2); // 64KB
  stt.write(big);
  assert.equal(streams[0]!.bytes, big.byteLength);
});

test("OUT_OF_RANGE(11) — 시간 한도·무음 타임아웃은 채널을 닫지 않고 다음 오디오에서 다시 연다", () => {
  const { streams, fatals, stt } = setup(600_000, 600_000);
  stt.write(silence(0.5));
  streams[0]!.emit("error", Object.assign(new Error("Audio Timeout"), { code: 11 }));
  assert.equal(fatals.length, 0);
  stt.write(silence(0.5));
  assert.equal(streams.length, 2);
});

test("그 밖의 오류는 치명적이다 — 코드만 알린다", () => {
  const { streams, fatals, stt } = setup(600_000, 600_000);
  stt.write(silence(0.5));
  streams[0]!.emit("error", Object.assign(new Error("PERMISSION_DENIED: 원문 같은 긴 설명"), { code: 7 }));
  assert.deepEqual(fatals, ["구글 STT 스트림 오류 code=7"]);
});

test("end() 뒤 남은 스트림이 다 닫히면 onEnd", () => {
  const { streams, stt, isEnded } = setup(600_000, 600_000);
  stt.write(silence(0.5));
  stt.end();
  assert.equal(isEnded(), false, "결과가 남았을 수 있다");
  streams[0]!.close();
  assert.equal(isEnded(), true);
});

test("오디오 없이 end() 하면 곧바로 onEnd", () => {
  const { stt, isEnded } = setup(600_000, 600_000);
  stt.end();
  assert.equal(isEnded(), true);
});
