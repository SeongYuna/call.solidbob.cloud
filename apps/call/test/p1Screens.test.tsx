// Requirement: QUA-1
/**
 * 류준 시연 인계(09-24판) P1 회귀 테스트.
 *
 * ④ `compliance_unavailable` — 검사가 돌지 못한 상담원 발화를 「탐지 미동작」으로 그린다
 *    (`w6-compliance-alert-ui` 완료 조건 2). 조용히 「위반 없음」처럼 보이면 안 된다.
 * ⑤ `fired: true, cards: []` — 그 발화 줄에 「관련 문서 없음」. 추천 메시지에 `segment_id` 가
 *    실려 올 때만 표시하고, 없으면 어느 발화였는지 추정하지 않는다.
 * ⑥ 수동 검색으로 먼저 띄운 조항에 나중에 F-2 판정이 오면 그 카드에 붙는다(두 장이 되지 않는다).
 */
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";
import { ComplianceUnavailableNotice } from "../src/components/ComplianceWarningBanner";
import { NoDocsNote } from "../src/components/TranscriptPanel";
import { parseCallMediatorMessage } from "../src/lib/ws/realCallMediatorClient";
import { useCallStore } from "../src/store/callStore";
import type { ClosureEvent, RecommendationCard } from "../src/types/contract";

function card(docId: string, title = `문서 ${docId}`): RecommendationCard {
  return {
    title,
    summary: "요약",
    source: { doc_id: docId, title: `출처 ${docId}` },
    similarity_score: 0.7,
    source_type: "auto",
  };
}

function closure(procedure: string): ClosureEvent {
  return {
    call_id: "demo-1",
    procedure,
    procedure_title: `절차 ${procedure}`,
    evidence: { 신분증: false },
    verdict: "incomplete",
    missing: ["신분증"],
    detected: true,
  };
}

beforeEach(() => {
  useCallStore.getState().resetCall();
  useCallStore.getState().applyStarted("demo-1");
});

describe("④ ComplianceUnavailableNotice", () => {
  it("「탐지 미동작」을 사실로만 쓰고 판정·상태 코드를 내지 않는다", () => {
    const html = renderToStaticMarkup(<ComplianceUnavailableNotice />);
    expect(html).toContain("탐지 미동작");
    expect(html).toContain("검사를 하지 못했습니다");
    expect(html).not.toMatch(/안전|위반 없음|위험도|501/);
  });

  it("스토어는 세그먼트별로 실패 신호를 담는다(화면이 읽는 키)", () => {
    useCallStore
      .getState()
      .applyComplianceUnavailable("7", { call_id: "demo-1", segment_id: 7, status: "501" });
    expect(useCallStore.getState().complianceUnavailable["7"]).toBeDefined();
  });
});

describe("⑤ 발화별 「관련 문서 없음」", () => {
  it("파서 — segment_id 가 실려 오면 읽고, 없으면 비워 둔다", () => {
    const withSeg = parseCallMediatorMessage({
      type: "recommendation",
      payload: {
        fired: "true",
        call_id: "demo-1",
        trigger_at_ms: "1500",
        internal_latency_ms: "40",
        cards: [],
        segment_id: "12",
      },
    });
    expect(withSeg?.kind === "recommendation" && withSeg.payload.segment_id).toBe("12");

    const withoutSeg = parseCallMediatorMessage({
      type: "recommendation",
      payload: {
        fired: "true",
        call_id: "demo-1",
        trigger_at_ms: "1500",
        internal_latency_ms: "40",
        cards: [],
      },
    });
    expect(withoutSeg?.kind).toBe("recommendation");
    expect(withoutSeg?.kind === "recommendation" && withoutSeg.payload.segment_id).toBeUndefined();
  });

  it("fired:true · 0장 · segment_id 있음 → 그 세그먼트에 표시", () => {
    useCallStore.getState().applyRecommendation([], "demo-1", 1500, true, "12");
    expect(useCallStore.getState().noDocsSegments).toEqual({ "12": true });
  });

  it("fired:false(검색 안 함)나 카드가 있으면 표시하지 않는다", () => {
    const store = useCallStore.getState();
    store.applyRecommendation([], "demo-1", 0, false, "3");
    store.applyRecommendation([card("DASAN-1")], "demo-1", 1500, true, "4");
    expect(useCallStore.getState().noDocsSegments).toEqual({});
  });

  it("segment_id 가 없으면 어느 발화였는지 추정하지 않는다", () => {
    useCallStore.getState().applyRecommendation([], "demo-1", 1500, true);
    expect(useCallStore.getState().noDocsSegments).toEqual({});
  });

  it("새 통화로 넘어가면 비워진다", () => {
    useCallStore.getState().applyRecommendation([], "demo-1", 1500, true, "12");
    useCallStore.getState().resetCall();
    expect(useCallStore.getState().noDocsSegments).toEqual({});
  });

  it("표시 문구는 「없다」로 단정하지 않고 「찾지 못했다」로 쓴다", () => {
    const html = renderToStaticMarkup(<NoDocsNote />);
    expect(html).toContain("관련 문서 없음");
    expect(html).toContain("찾지 못했습니다");
  });
});

describe("⑥ 수동 검색 카드에 나중 F-2 판정 붙이기", () => {
  it("같은 조항의 수동 카드에 붙고, 판정 전용 카드가 따로 생기지 않는다", () => {
    const store = useCallStore.getState();
    store.applyManualResult([card("DASAN-TERM-2.9")]);
    store.applyClosure(closure("DASAN-TERM-2.9"));

    const { cards } = useCallStore.getState();
    expect(cards).toHaveLength(1);
    expect(cards[0]?.card.source_type).toBe("manual");
    expect(cards[0]?.closure?.procedure).toBe("DASAN-TERM-2.9");
  });

  it("같은 조항의 자동 카드가 있으면 자동 카드가 먼저다", () => {
    const store = useCallStore.getState();
    store.applyManualResult([card("DASAN-TERM-2.9", "수동으로 찾은 제목")]);
    store.applyRecommendation([card("DASAN-TERM-2.9", "자동 추천 제목")], "demo-1", 1500, true);
    store.applyClosure(closure("DASAN-TERM-2.9"));

    const { cards } = useCallStore.getState();
    const withClosure = cards.filter((item) => item.closure !== null);
    expect(withClosure).toHaveLength(1);
    expect(withClosure[0]?.card.title).toBe("자동 추천 제목");
  });

  it("다른 조항의 수동 카드에는 붙지 않는다(판정 전용 카드가 생긴다)", () => {
    const store = useCallStore.getState();
    store.applyManualResult([card("DASAN-TERM-1.1")]);
    store.applyClosure(closure("DASAN-TERM-2.9"));

    const { cards } = useCallStore.getState();
    expect(cards).toHaveLength(2);
    expect(cards[0]?.closure).toBeNull();
    expect(cards[1]?.closure?.procedure).toBe("DASAN-TERM-2.9");
  });
});
