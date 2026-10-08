// Requirement: F-3
/**
 * 「통화받기」 전 고객 브리핑 카드 회귀 테스트(티켓 `w8-f3-briefing-card-ui`).
 *
 * ① 파서 — 필드가 빠지거나 `status` 가 모르는 값이면 던지지 않고 null(카드 없음, 오류 배너 없음).
 * ② 다섯 상태(ready · first_contact · unidentified · 실패 · 대기)가 각각 그려진다.
 * ③ 「추정」 꼬리표가 남고, 단정·점수 표현이 없다(절대 원칙 9 · 부록 A-1).
 *
 * DOM 환경 없이 `renderToStaticMarkup` 으로 그린다(효과·이벤트는 보지 않는다).
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { CustomerBriefingCard } from "../src/components/CustomerBriefingCard";
import { parseCustomerBriefing } from "../src/lib/api/coreClient";
import { briefingPreviewValue, readBriefingPreview } from "../src/mock/customerBriefing";

function readyWire(): Record<string, unknown> {
  return {
    call_id: "c-1",
    status: "ready",
    prior_call_count: "2",
    purpose: { category: "서류 보완", text: "위임장을 준비하다 막혀 다시 건 것으로 보입니다", source: "model" },
    briefing_lines: ["첫 줄", "둘째 줄", "셋째 줄"],
    evidence: [
      {
        call_id: "p-1",
        started_at: "2026-10-05T14:02:00+09:00",
        inquiry_type: "일반행정",
        summary_confirmed: "false",
        incomplete_procedures: ["DASAN-TERM-4.1"],
      },
    ],
    signals: { open_follow_ups: "1", call_guard_categories: ["insult"], blacklisted: "true" },
    generated_at: "2026-10-08T09:00:00+09:00",
  };
}

describe("parseCustomerBriefing", () => {
  it("문자열 값을 숫자·불리언으로 되돌린다", () => {
    const parsed = parseCustomerBriefing(readyWire());
    expect(parsed).not.toBeNull();
    expect(parsed?.priorCallCount).toBe(2);
    expect(parsed?.signals).toEqual({ openFollowUps: 1, callGuardCategories: ["insult"], blacklisted: true });
    expect(parsed?.evidence[0]?.summaryConfirmed).toBe(false);
    expect(parsed?.purpose?.source).toBe("model");
  });

  it("purpose 가 null 이어도 받는다", () => {
    expect(parseCustomerBriefing({ ...readyWire(), purpose: null })?.purpose).toBeNull();
  });

  it("모르는 status 면 null", () => {
    expect(parseCustomerBriefing({ ...readyWire(), status: "risky" })).toBeNull();
  });

  it.each(["call_id", "status", "prior_call_count", "briefing_lines", "evidence", "signals", "generated_at"])(
    "필드 %s 가 빠지면 null",
    (field) => {
      const wire = readyWire();
      delete wire[field];
      expect(parseCustomerBriefing(wire)).toBeNull();
    },
  );

  it("값 형식이 어긋나면 던지지 않고 null", () => {
    expect(parseCustomerBriefing(null)).toBeNull();
    expect(parseCustomerBriefing("ready")).toBeNull();
    expect(parseCustomerBriefing({ ...readyWire(), prior_call_count: "두 건" })).toBeNull();
    expect(
      parseCustomerBriefing({ ...readyWire(), purpose: { category: "재문의", text: "…", source: "llm" } }),
    ).toBeNull();
    expect(
      parseCustomerBriefing({
        ...readyWire(),
        signals: { open_follow_ups: "1", call_guard_categories: [], blacklisted: "maybe" },
      }),
    ).toBeNull();
    expect(
      parseCustomerBriefing({ ...readyWire(), evidence: [{ call_id: "p-1", started_at: "어제" }] }),
    ).toBeNull();
  });
});

const ASSERTIVE = [/위험/, /요주의/, /%/, /신뢰도/, /이 고객의/];

describe("CustomerBriefingCard", () => {
  it("ready — 추정 꼬리표 · 목적 · 세 줄 · 근거(초안) · 신호를 그린다", () => {
    const html = renderToStaticMarkup(<CustomerBriefingCard state={parseCustomerBriefing(readyWire())} />);
    expect(html).toContain("같은 번호로 걸려 온 지난 통화");
    expect(html).toContain("추정 통화 목적");
    expect(html).toContain("서류 보완");
    expect(html).not.toContain("규칙 요약");
    expect(html).toContain("셋째 줄");
    expect(html).toContain("10-05 · 일반행정");
    expect(html).toContain("초안");
    expect(html).toContain("마치지 않은 후속조치 1건");
    expect(html).toContain("블랙리스트 적용 중");
    expect(html).toContain("지난 통화에서 욕설·모욕 경고가 있었습니다");
    for (const pattern of ASSERTIVE) {
      expect(html).not.toMatch(pattern);
    }
  });

  it("source rule 이면 「규칙 요약」을 붙인다", () => {
    const wire = { ...readyWire(), purpose: { category: "후속 확인", text: "…", source: "rule" } };
    const html = renderToStaticMarkup(<CustomerBriefingCard state={parseCustomerBriefing(wire)} />);
    expect(html).toContain("추정 통화 목적");
    expect(html).toContain("규칙 요약");
  });

  it("first_contact · unidentified · 대기는 한 줄", () => {
    expect(renderToStaticMarkup(<CustomerBriefingCard state={briefingPreviewValue("first_contact")} />)).toContain(
      "첫 문의로 보입니다",
    );
    expect(renderToStaticMarkup(<CustomerBriefingCard state={briefingPreviewValue("unidentified")} />)).toContain(
      "발신 번호를 확인할 수 없어",
    );
    expect(renderToStaticMarkup(<CustomerBriefingCard state="loading" />)).toContain("브리핑 준비 중");
  });

  it("실패면 아무것도 그리지 않는다", () => {
    expect(renderToStaticMarkup(<CustomerBriefingCard state={null} />)).toBe("");
    expect(briefingPreviewValue("failed")).toBeNull();
  });
});

describe("mock 미리보기", () => {
  it("?briefing= 값을 읽고 모르는 값은 무시한다", () => {
    expect(readBriefingPreview("?briefing=ready")).toBe("ready");
    expect(readBriefingPreview("?briefing=nope")).toBeNull();
    expect(readBriefingPreview("")).toBeNull();
  });

  it("ready 예시는 파서를 통과한다", () => {
    expect(briefingPreviewValue("ready")).not.toBeNull();
    expect(briefingPreviewValue("ready-rule")).not.toBeNull();
  });
});
