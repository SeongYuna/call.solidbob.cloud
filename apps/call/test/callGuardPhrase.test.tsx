// Requirement: QUA-1
/**
 * C-6 콜 가드 — 서버가 보내는 걸린 표현(`phrase`)을 파서가 버리지 않고 배너가 그린다.
 * 서버 `call_guard_dto.py` 는 `{category, phrase, span, source_doc_id}` 를 보낸다(마스킹된 자막에서 자른 값).
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CallGuardPhrase } from "../src/components/TranscriptPanel";
import { parseCallMediatorMessage } from "../src/lib/ws/realCallMediatorClient";

function parse(flags: unknown[]) {
  return parseCallMediatorMessage({
    type: "call_guard",
    payload: { call_id: "demo-1", segment_id: "8", flags },
  });
}

describe("call_guard 파서 — phrase", () => {
  it("phrase 를 읽어 flag 에 싣는다", () => {
    const message = parse([
      { category: "insult", phrase: "이 멍청한", span: ["0", "5"], source_doc_id: "DASAN-MANUAL-5.1" },
    ]);
    expect(message?.kind).toBe("call_guard");
    if (message?.kind !== "call_guard") {
      return;
    }
    expect(message.payload.flags).toEqual([
      { segment_id: 8, category: "insult", phrase: "이 멍청한" },
    ]);
  });

  it("phrase 가 없거나 비었으면 싣지 않는다(갈래 안내만)", () => {
    const message = parse([{ category: "threat" }, { category: "distress", phrase: "  " }]);
    if (message?.kind !== "call_guard") {
      throw new Error("call_guard 로 파싱되지 않았다");
    }
    expect(message.payload.flags).toEqual([
      { segment_id: 8, category: "threat" },
      { segment_id: 8, category: "distress" },
    ]);
  });
});

describe("CallGuardPhrase", () => {
  it("걸린 표현만 보이고 점수·위험도는 없다", () => {
    const html = renderToStaticMarkup(<CallGuardPhrase phrase="가만 안 둘" />);
    expect(html).toContain("「가만 안 둘」");
    expect(html).not.toMatch(/위험도|%|점/);
  });
});
