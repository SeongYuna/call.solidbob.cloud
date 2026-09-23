// Requirement: QUA-1
/**
 * WS 파서 회귀 테스트 — services/call-mediator 가 실제로 방송하는 JSON 모양 그대로
 * 검증한다. §7.3 계약: 숫자·불린도 문자열로 온다("true"·"1500") — 이 모양이 아니면
 * `readNumber`/`readBoolean`이 `null`을 돌려주고 화면은 그 이벤트를 버린다(`w6-frontend-tests-vitest`).
 *
 * 표본은 `services/call-mediator/test/ws_server.test.ts`("대시보드 파서가 받는
 * 형식 그대로다")가 실측한 방송 payload와 `ports.ts`의 타입 정의를 따랐다.
 */
import { describe, expect, it } from "vitest";
import { parseCallMediatorMessage } from "../src/lib/ws/realCallMediatorClient";

describe("parseCallMediatorMessage — 알 수 없는 메시지", () => {
  it("타입 태그가 없거나 모르는 값이면 null — 화면이 「알 수 없는 메시지」 오류로 처리한다", () => {
    expect(parseCallMediatorMessage({ type: "no-such-kind", payload: {} })).toBeNull();
    expect(parseCallMediatorMessage("문자열")).toBeNull();
    expect(parseCallMediatorMessage(null)).toBeNull();
  });
});

describe("parseCallMediatorMessage — started(통화 시작)", () => {
  it("call_id 하나만 온 통화 시작 신호를 읽는다(w6-close-callid-missing)", () => {
    const message = parseCallMediatorMessage({
      type: "started",
      payload: { call_id: "test-1" },
    });
    expect(message).toEqual({ kind: "started", payload: { call_id: "test-1" } });
  });

  it("call_id 가 없으면 버린다", () => {
    expect(parseCallMediatorMessage({ type: "started", payload: {} })).toBeNull();
  });
});

describe("parseCallMediatorMessage — transcript(자막)", () => {
  it("마스킹된 자막 한 줄을 숫자·불린으로 변환해 읽는다", () => {
    const message = parseCallMediatorMessage({
      type: "transcript",
      payload: {
        call_id: "test-1",
        segment_id: "3",
        speaker: "customer",
        text: "전화번호는 ***-****-****",
        masked: [{ type: "P4", span: ["6", "18"] }],
        is_final: "true",
        utterance_end_ms: "1500",
      },
    });
    expect(message).toEqual({
      kind: "transcript",
      payload: {
        call_id: "test-1",
        segment_id: "3",
        speaker: "customer",
        text: "전화번호는 ***-****-****",
        masked: [{ type: "P4", span: [6, 18] }],
        is_final: true,
        utterance_end_ms: 1500,
      },
    });
  });

  it("불린이 문자열이 아니면(계약 위반) 버린다 — 조용히 잘못 그리지 않는다", () => {
    const originalAlert = globalThis.alert;
    globalThis.alert = () => {};
    try {
      const message = parseCallMediatorMessage({
        type: "transcript",
        payload: {
          call_id: "test-1",
          segment_id: "3",
          speaker: "customer",
          text: "안녕하세요",
          masked: [],
          is_final: true, // 문자열 "true" 가 아니라 boolean — 서버 필드가 바뀐 상황을 흉내
          utterance_end_ms: "1500",
        },
      });
      expect(message).toBeNull();
    } finally {
      globalThis.alert = originalAlert;
    }
  });
});

describe("parseCallMediatorMessage — recommendation(추천)", () => {
  it("트리거가 발동한 배치를 읽는다", () => {
    const message = parseCallMediatorMessage({
      type: "recommendation",
      payload: {
        fired: "true",
        call_id: "test-1",
        trigger_at_ms: "800",
        internal_latency_ms: "420",
        cards: [
          {
            title: "주민등록초본 발급",
            summary: "본인 신청 시 신분증만 지참하면 발급됩니다.",
            source: { doc_id: "DASAN-TERM-4.3", title: "주민등록초본 발급" },
            similarity_score: "0.87",
            card_id: "card-1",
          },
        ],
      },
    });
    expect(message).toEqual({
      kind: "recommendation",
      payload: {
        fired: true,
        call_id: "test-1",
        trigger_at_ms: 800,
        internal_latency_ms: 420,
        cards: [
          {
            title: "주민등록초본 발급",
            summary: "본인 신청 시 신분증만 지참하면 발급됩니다.",
            source: { doc_id: "DASAN-TERM-4.3", title: "주민등록초본 발급" },
            similarity_score: 0.87,
            card_id: "card-1",
          },
        ],
      },
    });
  });

  it("fired:false 면 call_id·cards 가 없어도 읽는다 — 트리거 미발동은 검색조차 안 한다", () => {
    const message = parseCallMediatorMessage({ type: "recommendation", payload: { fired: "false" } });
    expect(message).toEqual({
      kind: "recommendation",
      payload: { fired: false, call_id: "", trigger_at_ms: 0, internal_latency_ms: 0, cards: [] },
    });
  });
});

describe("parseCallMediatorMessage — compliance(컴플라이언스)", () => {
  it("상담원 발화 한 줄에 잡힌 위반 여러 건을 읽는다", () => {
    const message = parseCallMediatorMessage({
      type: "compliance",
      payload: {
        segment_id: "7",
        findings: [
          {
            rule_code: "C-1-과잉확신",
            phrase: "무조건 됩니다",
            alternative_source: { doc_id: "DASAN-MANUAL-2.1", title: "안내 표현 지침" },
          },
          { rule_code: "C-2-단정", phrase: "무조건 감면돼요" },
        ],
      },
    });
    expect(message).toEqual({
      kind: "compliance",
      payload: {
        segment_id: "7",
        findings: [
          {
            segment_id: 7,
            rule_code: "C-1-과잉확신",
            phrase: "무조건 됩니다",
            alternative_source: { doc_id: "DASAN-MANUAL-2.1", title: "안내 표현 지침" },
          },
          { segment_id: 7, rule_code: "C-2-단정", phrase: "무조건 감면돼요" },
        ],
      },
    });
  });

  it("findings 가 배열이 아니면 버린다", () => {
    expect(
      parseCallMediatorMessage({ type: "compliance", payload: { segment_id: "7", findings: "없음" } }),
    ).toBeNull();
  });
});

describe("parseCallMediatorMessage — closure(필요서류 판정 종료)", () => {
  it("필요서류 판정을 읽는다 — 미충족 항목·출처 포함", () => {
    const message = parseCallMediatorMessage({
      type: "closure",
      payload: {
        call_id: "test-1",
        procedure: "DASAN-TERM-4.3",
        procedure_title: "주민등록초본 발급",
        verdict: "incomplete",
        detected: "true",
        evidence: { 신분증: "true", 위임장: "false" },
        missing: ["위임장"],
        source: { doc_id: "DASAN-TERM-4.3", title: "주민등록초본 발급" },
      },
    });
    expect(message).toEqual({
      kind: "closure",
      payload: {
        call_id: "test-1",
        procedure: "DASAN-TERM-4.3",
        procedure_title: "주민등록초본 발급",
        verdict: "incomplete",
        detected: true,
        evidence: { 신분증: true, 위임장: false },
        missing: ["위임장"],
        source: { doc_id: "DASAN-TERM-4.3", title: "주민등록초본 발급" },
      },
    });
  });

  it("verdict 가 계약 밖 값이면(옛 approved/blocked 등) 버린다", () => {
    expect(
      parseCallMediatorMessage({
        type: "closure",
        payload: {
          call_id: "test-1",
          procedure: "DASAN-TERM-4.3",
          verdict: "approved",
          detected: "true",
          evidence: {},
          missing: [],
        },
      }),
    ).toBeNull();
  });
});
