// Requirement: C-6
/**
 * C-6 베타 폭언 대응 단계 회귀 테스트(티켓 `w8-c6-intervention-overlay-ui`, `decisions/221`).
 *
 * ① 파서 — 미디에이터 `CallGuardInterventionPayload`(값은 전부 문자열)를 읽는다. 모르는 `stage`·빠진 필드는
 *    **오류 배너 없이** 버린다(`ignored`).
 * ② 저장소 — 1·2차는 덮개, 종료 권고는 덮개를 걷고 배너. 새 통화면 둘 다 지운다.
 * ③ 화면 — 「베타」 꼬리표, 「고객 안내 문구」(「고객에게 안내했습니다」 아님), 종료 버튼 없음, 점수 표현 없음.
 * ④ mock — `?c6beta=1` 일 때만 세 단계를 재생한다.
 *
 * DOM 환경 없이 `renderToStaticMarkup` 으로 그린다(효과·이벤트는 보지 않는다).
 */
import { renderToStaticMarkup } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  CallGuardEndSuggestionBannerView,
  CallGuardPauseOverlayView,
} from "../src/components/CallGuardInterventionLayer";
import { RealCallMediatorClient, parseCallMediatorMessage } from "../src/lib/ws/realCallMediatorClient";
import type { CallMediatorListener } from "../src/lib/ws/types";
import { isCallGuardBetaPreview } from "../src/mock/callGuardBeta";
import { callGuardKoScenario } from "../src/mock/scenarios/callGuardKo";
import { useCallStore } from "../src/store/callStore";
import type { CallGuardIntervention } from "../src/types/contract";

function wire(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    type: "call_guard_intervention",
    payload: {
      call_id: "test-1",
      segment_id: "12",
      stage: "warning",
      abuse_count: "1",
      pause_ms: "8000",
      announcement: "고객님, 원활한 상담을 위해 업무와 무관한 표현은 삼가 주시기 바랍니다.",
      source_doc_id: "DASAN-MANUAL-5.1",
      beta: "true",
      ...overrides,
    },
  };
}

const WARNING: CallGuardIntervention = {
  call_id: "test-1",
  segment_id: 12,
  stage: "warning",
  abuse_count: 1,
  pause_ms: 8000,
  announcement: "고객님, 원활한 상담을 위해 업무와 무관한 표현은 삼가 주시기 바랍니다.",
  source_doc_id: "DASAN-MANUAL-5.1",
};

const END: CallGuardIntervention = {
  call_id: "test-1",
  segment_id: 14,
  stage: "end_suggested",
  abuse_count: 3,
  pause_ms: 0,
  announcement: null,
  source_doc_id: "DASAN-MANUAL-5.2",
};

describe("parseCallMediatorMessage — call_guard_intervention(C-6 베타)", () => {
  it("문자열 값을 숫자로 되돌려 읽는다", () => {
    expect(parseCallMediatorMessage(wire())).toEqual({ kind: "call_guard_intervention", payload: WARNING });
  });

  it("end_suggested 는 안내 문구 null · pause 0 으로 받는다", () => {
    const message = parseCallMediatorMessage(
      wire({ stage: "end_suggested", abuse_count: "3", pause_ms: "0", announcement: null, segment_id: "14", source_doc_id: "DASAN-MANUAL-5.2" }),
    );
    expect(message).toEqual({ kind: "call_guard_intervention", payload: END });
  });

  it.each([
    ["모르는 stage", { stage: "hang_up" }],
    ["segment_id 없음", { segment_id: undefined }],
    ["pause_ms 숫자 아님", { pause_ms: "길게" }],
    ["source_doc_id 없음", { source_doc_id: undefined }],
    ["beta 표시 없음", { beta: undefined }],
    ["1차인데 안내 문구 없음", { announcement: null }],
    ["1차인데 pause 0", { pause_ms: "0" }],
  ])("%s → 오류가 아니라 ignored", (_label, overrides) => {
    expect(parseCallMediatorMessage(wire(overrides))).toEqual({ kind: "ignored" });
  });

  it("형식이 어긋난 대응 메시지는 오류 배너를 띄우지 않고, 맞는 것은 콜백으로 넘긴다", () => {
    const onError = vi.fn();
    const onCallGuardIntervention = vi.fn();
    const client = new RealCallMediatorClient("ws://localhost/ws") as unknown as {
      listeners: Partial<CallMediatorListener>;
      handleMessage: (raw: string) => void;
    };
    client.listeners = { onError, onCallGuardIntervention };
    client.handleMessage(JSON.stringify(wire({ stage: "hang_up" })));
    expect(onError).not.toHaveBeenCalled();
    expect(onCallGuardIntervention).not.toHaveBeenCalled();
    client.handleMessage(JSON.stringify(wire()));
    expect(onCallGuardIntervention).toHaveBeenCalledWith(WARNING);
    expect(onError).not.toHaveBeenCalled();
  });
});

describe("callStore — 대응 단계", () => {
  beforeEach(() => {
    useCallStore.getState().resetCall();
  });

  it("1차는 pause_ms 동안 덮개를 띄운다", () => {
    useCallStore.getState().applyCallGuardIntervention(WARNING, 1_000);
    expect(useCallStore.getState().callGuardPause).toEqual({ intervention: WARNING, endsAt: 9_000 });
    expect(useCallStore.getState().callGuardEndSuggestion).toBeNull();
  });

  it("종료 권고는 덮개를 걷고 배너를 남긴다 — 통화 상태는 건드리지 않는다", () => {
    const before = useCallStore.getState().phase;
    useCallStore.getState().applyCallGuardIntervention(WARNING, 1_000);
    useCallStore.getState().applyCallGuardIntervention(END, 2_000);
    expect(useCallStore.getState().callGuardPause).toBeNull();
    expect(useCallStore.getState().callGuardEndSuggestion).toEqual(END);
    expect(useCallStore.getState().phase).toBe(before);
  });

  it("상담원이 닫을 수 있고, 새 통화면 둘 다 지운다", () => {
    useCallStore.getState().applyCallGuardIntervention(WARNING);
    useCallStore.getState().dismissCallGuardPause();
    expect(useCallStore.getState().callGuardPause).toBeNull();
    useCallStore.getState().applyCallGuardIntervention(WARNING);
    useCallStore.getState().applyCallGuardIntervention(END);
    useCallStore.getState().resetCall();
    expect(useCallStore.getState().callGuardPause).toBeNull();
    expect(useCallStore.getState().callGuardEndSuggestion).toBeNull();
  });
});

const ASSERTIVE = [/위험/, /요주의/, /%/, /점수/, /고객에게 안내했습니다/];

describe("화면 — 덮개 · 종료 권고", () => {
  it("1차 덮개: 베타 · (1차) · 고객 안내 문구 · 남은 시간 · 닫기", () => {
    const html = renderToStaticMarkup(
      <CallGuardPauseOverlayView intervention={WARNING} remainingSeconds={8} onDismiss={() => {}} />,
    );
    expect(html).toContain("베타");
    expect(html).toContain("일시정지 — 고객 안내 중 (1차)");
    expect(html).toContain("고객 안내 문구");
    expect(html).toContain(WARNING.announcement ?? "");
    expect(html).toContain("8초 뒤 걷힙니다");
    expect(html).toContain("이 PC 에서만");
    expect(html).toContain("덮개 닫기");
    for (const pattern of ASSERTIVE) {
      expect(html).not.toMatch(pattern);
    }
  });

  it("2차 덮개는 (2차)", () => {
    const html = renderToStaticMarkup(
      <CallGuardPauseOverlayView
        intervention={{ ...WARNING, stage: "final_warning", abuse_count: 2 }}
        remainingSeconds={3}
        onDismiss={() => {}}
      />,
    );
    expect(html).toContain("(2차)");
  });

  it("종료 권고: 덮개 없이 배너만, 종료 버튼 없음", () => {
    expect(
      renderToStaticMarkup(<CallGuardPauseOverlayView intervention={END} remainingSeconds={0} onDismiss={() => {}} />),
    ).toBe("");
    const html = renderToStaticMarkup(<CallGuardEndSuggestionBannerView intervention={END} onDismiss={() => {}} />);
    expect(html).toContain("베타");
    expect(html).toContain("매뉴얼 5.1·5.2 — 통화 종료를 판단할 수 있습니다. 종료 여부는 상담원이 정합니다");
    // 버튼은 「권고 닫기」 하나뿐 — 통화를 끊는 버튼을 만들지 않는다.
    expect(html.match(/<button/g)?.length).toBe(1);
    expect(html).toContain('aria-label="권고 닫기"');
    for (const pattern of ASSERTIVE) {
      expect(html).not.toMatch(pattern);
    }
  });
});

describe("mock — ?c6beta=1", () => {
  it("스위치는 c6beta=1 일 때만 켜진다", () => {
    expect(isCallGuardBetaPreview("?c6beta=1")).toBe(true);
    expect(isCallGuardBetaPreview("?c6beta=0")).toBe(false);
    expect(isCallGuardBetaPreview("")).toBe(false);
  });

  it("ko-callguard 베타 재생은 1차 → 2차 → 종료 권고, 각 단계에 콜가드 폭언이 있다", () => {
    const beta = callGuardKoScenario.callGuardBeta;
    expect(beta).toBeDefined();
    const stages = Object.values(beta?.interventions ?? {})
      .sort((a, b) => a.abuse_count - b.abuse_count)
      .map((i) => i.stage);
    expect(stages).toEqual(["warning", "final_warning", "end_suggested"]);
    for (const segmentId of Object.keys(beta?.interventions ?? {})) {
      const flag = callGuardKoScenario.callGuard?.[segmentId] ?? beta?.extraCallGuard[segmentId];
      expect(flag?.category).toBe("insult");
    }
  });
});
