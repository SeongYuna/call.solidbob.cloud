// Requirement: F-2, B-3, QUA-1
/**
 * `w6-closure-card-pairing` 회귀 테스트 — 추천 묶음이 둘 이상 쌓인 뒤 **앞 묶음** 1순위 조항의
 * 판정이 와도, 그 조항을 실제로 띄운 카드에 붙는다(가장 최근의 판정 없는 카드가 아니라).
 * 판정과 같은 문서를 띄운 카드가 없으면 남의 카드에 붙이지 않고 판정 전용 카드를 새로 만든다.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { useCallStore } from "../src/store/callStore";
import type { ClosureEvent, RecommendationCard } from "../src/types/contract";

function card(docId: string, title: string): RecommendationCard {
  return {
    title,
    summary: "요약",
    source: { doc_id: docId, title },
    similarity_score: 0.7,
    source_type: "auto",
  };
}

function closure(procedure: string): ClosureEvent {
  return {
    call_id: "demo-1",
    procedure,
    evidence: { 신분증: false },
    verdict: "incomplete",
    missing: ["신분증"],
    detected: "true",
  } as ClosureEvent;
}

describe("callStore — 필요서류 판정은 그 조항을 띄운 카드에 붙는다", () => {
  beforeEach(() => {
    useCallStore.getState().resetCall();
    useCallStore.getState().applyStarted("demo-1");
  });

  it("추천 두 묶음 뒤에 앞 묶음 1순위 조항의 판정이 와도 앞 카드에 붙는다", () => {
    const store = useCallStore.getState();
    store.applyRecommendation([card("DASAN-TERM-4.3", "주민등록초본 발급")], "demo-1", 1000, true);
    store.applyRecommendation([card("DASAN-TERM-3.5", "수도 사용자 명의변경")], "demo-1", 2000, true);
    useCallStore.getState().applyClosure(closure("DASAN-TERM-4.3"));

    const cards = useCallStore.getState().cards;
    const attached = cards.filter((item) => item.closure !== null);
    expect(attached).toHaveLength(1);
    expect(attached[0]!.card.source.doc_id).toBe("DASAN-TERM-4.3");
    expect(attached[0]!.card.title).toBe("주민등록초본 발급");
    // 뒤 묶음(3.5) 카드에는 아무것도 붙지 않았다
    const other = cards.find((item) => item.card.source.doc_id === "DASAN-TERM-3.5");
    expect(other?.closure ?? null).toBeNull();
  });

  it("같은 절차의 판정이 다시 오면 같은 카드를 갱신한다 — 카드가 늘지 않는다", () => {
    const store = useCallStore.getState();
    store.applyRecommendation([card("DASAN-TERM-4.3", "주민등록초본 발급")], "demo-1", 1000, true);
    useCallStore.getState().applyClosure(closure("DASAN-TERM-4.3"));
    const before = useCallStore.getState().cards.length;
    useCallStore.getState().applyClosure({ ...closure("DASAN-TERM-4.3"), evidence: { 신분증: true }, missing: [], verdict: "complete" } as ClosureEvent);
    const cards = useCallStore.getState().cards;
    expect(cards).toHaveLength(before);
    expect(cards.find((item) => item.closure !== null)?.closure?.evidence).toEqual({ 신분증: true });
  });

  it("그 조항을 띄운 카드가 없으면 남의 카드에 붙이지 않고 판정 전용 카드를 만든다", () => {
    const store = useCallStore.getState();
    store.applyRecommendation([card("DASAN-TERM-6.12", "지원금 사칭 사기 주의")], "demo-1", 1000, true);
    useCallStore.getState().applyClosure(closure("DASAN-TERM-4.3"));
    const cards = useCallStore.getState().cards;
    const fraud = cards.find((item) => item.card.source.doc_id === "DASAN-TERM-6.12");
    expect(fraud?.closure ?? null).toBeNull();
    const own = cards.find((item) => item.closure?.procedure === "DASAN-TERM-4.3");
    expect(own).toBeDefined();
    expect(own!.card.source.doc_id).toBe("DASAN-TERM-4.3");
  });
});
