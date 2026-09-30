// Requirement: C-6, C-1, F-2, QUA-1
/**
 * 2026-09-30 수동 QA 2회차(`jekyll/_logs/2026-09-30-01-seongyun.md`)에서 남긴 화면 결함의 회귀 테스트.
 * Q-29·Q-30 갈래별 콜 가드 문구 · 근거 합산 칩 · 「권장 표현」 머리말 · 카드 요약 마크다운.
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { InlineMarkdown } from "../src/components/InlineMarkdown";
import { CALL_GUARD_COPY, complianceLabel } from "../src/components/TranscriptPanel";
import { pendingTally, type PanelCard } from "../src/store/callStore";
import type { ClosureEvent } from "../src/types/contract";

describe("CALL_GUARD_COPY — 갈래별 안내가 매뉴얼 5장을 따른다", () => {
  it("협박·성적 표현은 5.2(1차 안내 뒤 종료 가능), 욕설은 5.1, 위기 신호는 5.4 다", () => {
    expect(CALL_GUARD_COPY.threat.source).toBe("DASAN-MANUAL-5.2");
    expect(CALL_GUARD_COPY.sexual.source).toBe("DASAN-MANUAL-5.2");
    expect(CALL_GUARD_COPY.insult.source).toBe("DASAN-MANUAL-5.1");
    expect(CALL_GUARD_COPY.distress.source).toBe("DASAN-MANUAL-5.4");
    expect(CALL_GUARD_COPY.threat.hint).toContain("종료");
    expect(CALL_GUARD_COPY.distress.hint).toContain("끊지 말고");
  });
  it("「안내는 이어가시면 됩니다」 같은 한 줄 공통 문구가 없고, 위험도·점수·「안전」 표현이 없다(부록 A-1)", () => {
    for (const copy of Object.values(CALL_GUARD_COPY)) {
      expect(copy.hint).not.toContain("이어가시면");
      expect(`${copy.pill} ${copy.hint}`).not.toMatch(/위험도|%|안전합니다/);
    }
    expect(CALL_GUARD_COPY.threat.pill).toBe("🚫 상담원 보호 알림");
  });
});

describe("complianceLabel", () => {
  it("값이 조항 ID 면 「근거 조항」, 대체 표현이면 「권장 표현」", () => {
    expect(complianceLabel("DASAN-MANUAL-1.2")).toBe("근거 조항");
    expect(complianceLabel(" DASAN-TERM-4.3 ")).toBe("근거 조항");
    expect(complianceLabel("확인해 보겠습니다")).toBe("권장 표현");
    expect(complianceLabel("권장 대체 표현이 등록되지 않았습니다.")).toBe("권장 표현");
  });
});

function card(closure: ClosureEvent | null, settled: boolean): PanelCard {
  return {
    card: {
      title: "t",
      summary: "",
      source: { doc_id: "DASAN-TERM-4.3", title: "4.3" },
      similarity_score: 0.7,
      source_type: "auto",
    },
    trigger_at_ms: 0,
    closure,
    settled,
  } as PanelCard;
}
function closure(evidence: Record<string, boolean>): ClosureEvent {
  return {
    call_id: "c",
    procedure: "DASAN-TERM-4.3",
    evidence,
    verdict: "incomplete",
    missing: Object.keys(evidence).filter((k) => !evidence[k]),
    detected: "true",
  } as ClosureEvent;
}

describe("pendingTally — 진행 중인 판정 전부를 합친다", () => {
  it("카드 둘이면 둘을 더한다 · 정착된 카드와 판정 없는 카드는 뺀다", () => {
    const cards = [
      card(closure({ 신분증: true, 위임장: false }), false),
      card(closure({ 여권: false }), false),
      card(closure({ 등본: true }), true),
      card(null, false),
    ];
    expect(pendingTally(cards)).toEqual({ met: 1, total: 3 });
  });
  it("진행 중인 판정이 없으면 null", () => {
    expect(pendingTally([card(null, false), card(closure({ a: true }), true)])).toBeNull();
  });
});

describe("InlineMarkdown", () => {
  it("**굵게** 와 `코드` 만 바꾸고 나머지는 글자 그대로", () => {
    const html = renderToStaticMarkup(<InlineMarkdown text="구비서류: **신분증** 과 `여권` <b>x</b>" />);
    expect(html).toContain("<strong>신분증</strong>");
    expect(html).toContain("<code>여권</code>");
    expect(html).not.toContain("**");
    expect(html).toContain("&lt;b&gt;x&lt;/b&gt;");
  });
});
