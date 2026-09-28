// Requirement: QUA-1
/**
 * `w6-close-callid-missing` 회귀 테스트 — 비었거나 없는 `call_id` 가 이미 잡아 둔
 * `callId` 를 덮어쓰지 않는다. 서버는 트리거 미발동 응답(`fired: false`)에 `call_id` 를
 * 싣지 않고, 파서는 그 자리를 `""` 로 채운다. 통화 후 요약·확정·블랙리스트 버튼은
 * `callId.length > 0` 일 때만 뜨므로(`CallSummaryPanel`), 덮어쓰이면 통화를 닫을 수 없다.
 *
 * 콜 미디에이터 0.2.10 이 추천 메시지에 `call_id` 를 늘 싣게 돼 지금은 증상이 가려져
 * 있다 — 화면 쪽이 그것에 기대지 않는지를 여기서 본다.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { parseCallMediatorMessage } from "../src/lib/ws/realCallMediatorClient";
import { keepCallId, useCallStore } from "../src/store/callStore";

describe("keepCallId", () => {
  it("새 값이 있으면 새 값", () => {
    expect(keepCallId("call-2", "call-1")).toBe("call-2");
  });

  it("새 값이 비었으면 이미 잡아 둔 값", () => {
    expect(keepCallId("", "call-1")).toBe("call-1");
    expect(keepCallId("", null)).toBeNull();
  });
});

describe("callStore — callId 를 빈 값으로 덮어쓰지 않는다", () => {
  beforeEach(() => {
    useCallStore.getState().resetCall();
    useCallStore.getState().applyStarted("demo-syn004-01");
  });

  it("call_id 없는 fired:false 추천이 와도 callId 가 유지된다(파서 → 스토어)", () => {
    const message = parseCallMediatorMessage({
      type: "recommendation",
      payload: { fired: "false", trigger_at_ms: "0", internal_latency_ms: "3" },
    });
    expect(message?.kind).toBe("recommendation");
    if (message?.kind !== "recommendation") {
      return;
    }
    // 파서는 없는 call_id 를 "" 로 채운다 — 이 값이 스토어로 그대로 넘어간다.
    expect(message.payload.call_id).toBe("");

    const batch = message.payload;
    useCallStore
      .getState()
      .applyRecommendation(batch.cards, batch.call_id, batch.trigger_at_ms, batch.fired);

    expect(useCallStore.getState().callId).toBe("demo-syn004-01");
    expect(useCallStore.getState().lastFired).toBe(false);
  });

  it("카드가 붙는 추천이라도 call_id 가 비었으면 유지된다", () => {
    useCallStore.getState().applyRecommendation(
      [
        {
          title: "분실물 신고",
          summary: "요약",
          source: { doc_id: "DASAN-1", title: "분실물 안내" },
          similarity_score: 0.7,
          source_type: "auto",
        },
      ],
      "",
      1500,
      true,
    );
    expect(useCallStore.getState().callId).toBe("demo-syn004-01");
    expect(useCallStore.getState().cards).toHaveLength(1);
  });

  it("추천 0건 통화도 종료 시점에 callId 가 남아 요약·확정·블랙리스트 버튼 조건을 만족한다", () => {
    const store = useCallStore.getState();
    store.applyRecommendation([], "", 0, false);
    store.applyRecommendation([], "", 0, false);
    store.endCall();

    const { callId, cards } = useCallStore.getState();
    expect(cards).toHaveLength(0);
    // CallSummaryPanel 의 버튼 조건: callId.length > 0
    expect(callId).not.toBeNull();
    expect((callId ?? "").length).toBeGreaterThan(0);
  });

  it("실제 call_id 가 오면 그 값으로 바뀐다", () => {
    useCallStore.getState().applyRecommendation([], "demo-syn004-02", 0, false);
    expect(useCallStore.getState().callId).toBe("demo-syn004-02");
  });
});
