// Requirement: QUA-1
/**
 * 빈 상태 문구 · 오버라이드 배너 토큰 가리기 회귀 테스트.
 *
 * ① `decisions/219`(F-2 절차 채택 점수 하한 0.635) 이후 「통화 내내 절차가 하나도 안
 *    잡히는」 상태가 정상 동작으로 생긴다. 이때 문구가 「대상이 아니다 / 필요 없다」로
 *    **없다고 단정하지 않는지** 본다(부록 A-1).
 * ② `?call_mediator=` 배너는 시연 녹화 화면에 찍힌다 — 토큰 원문이 나가면 안 된다.
 *
 * DOM 환경 없이 `renderToStaticMarkup` 으로 그린다(효과·이벤트는 보지 않는다).
 */
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ClosureCardList, PopupEmptyState } from "../src/components/TermsPanel";
import {
  CallMediatorOverrideBannerView,
  redactTokenInUrl,
} from "../src/components/CallMediatorOverrideBanner";
import type { PanelCard } from "../src/store/callStore";

const ASSERTIVE = [/대상이 아닙니다/, /필요 없습니다/, /필요한 민원이 아직 없습니다/];

function expectNotAssertive(html: string): void {
  for (const pattern of ASSERTIVE) {
    expect(html).not.toMatch(pattern);
  }
}

function popupCard(docId: string): PanelCard {
  return {
    card: {
      title: `문서 ${docId}`,
      summary: "요약",
      source: { doc_id: docId, title: `출처 ${docId}` },
      similarity_score: 0.6,
      source_type: "auto",
    },
    trigger_at_ms: 1500,
    closure: null,
    settled: false,
  };
}

describe("PopupEmptyState — 팝업창 탭이 비었을 때", () => {
  it("fired:false 는 「검색하지 않았다」로 읽힌다 — 서류 안내 대상이 아니라고 단정하지 않는다", () => {
    const html = renderToStaticMarkup(
      <PopupEmptyState loading={false} lastFired={false} />,
    );
    expect(html).toContain("아직 검색할 문의 내용이 없습니다");
    expectNotAssertive(html);
  });

  it("응답 전·발동 후 0장은 「아직 없다」", () => {
    for (const lastFired of [null, true]) {
      const html = renderToStaticMarkup(
        <PopupEmptyState loading={false} lastFired={lastFired} />,
      );
      expect(html).toContain("관련 문서가 아직 없습니다");
      expectNotAssertive(html);
    }
  });

  it("응답을 기다리는 중이면 로딩 표시", () => {
    const html = renderToStaticMarkup(
      <PopupEmptyState loading lastFired={null} />,
    );
    expect(html).toContain("서류 불러오는 중");
  });
});

describe("ClosureCardList — 절차가 하나도 안 잡힌 필요서류 탭", () => {
  it("카드도 절차도 없으면 「아직 못 찾았다」 + 팝업창·수동 검색 안내", () => {
    const html = renderToStaticMarkup(
      <ClosureCardList cards={[]} onShowPopup={() => {}} />,
    );
    expect(html).toContain("아직 확실한 절차를 찾지 못했습니다");
    expect(html).toContain("수동 검색");
    expect(html).not.toContain("closure-empty-popup-link");
    expectNotAssertive(html);
  });

  it("카드는 있는데 closure 가 하나도 없으면 팝업창으로 유도한다(점수 하한 아래 통화)", () => {
    const html = renderToStaticMarkup(
      <ClosureCardList
        cards={[popupCard("DASAN-1"), popupCard("DASAN-2")]}
        onShowPopup={() => {}}
      />,
    );
    expect(html).toContain("아직 확실한 절차를 찾지 못했습니다");
    expect(html).toContain("closure-empty-popup-link");
    expect(html).toContain("관련 문서 2건 보기");
    // 절차 없는 카드는 필요서류 탭 목록에 그리지 않는다
    expect(html).not.toContain("term-card-list");
    expectNotAssertive(html);
  });
});

describe("redactTokenInUrl — 오버라이드 배너", () => {
  it("token 값을 *** 로 가리고 나머지는 그대로 둔다", () => {
    const url = "wss://server.solidbob.cloud/call-mediator?token=cga_SECRET123&call_id=demo-1";
    const shown = redactTokenInUrl(url);
    expect(shown).toBe("wss://server.solidbob.cloud/call-mediator?token=***&call_id=demo-1");
    expect(shown).not.toContain("cga_SECRET123");
  });

  it("이름에 token 이 든 쿼리는 전부 가린다(agent_token·call_token)", () => {
    const shown = redactTokenInUrl(
      "wss://x.example/ws?agent_token=AAA&call_token=BBB#frag",
    );
    expect(shown).toBe("wss://x.example/ws?agent_token=***&call_token=***#frag");
  });

  it("토큰이 없으면 주소를 바꾸지 않는다", () => {
    const url = "ws://localhost:8787/ws?call_id=demo-1";
    expect(redactTokenInUrl(url)).toBe(url);
  });
});

describe("CallMediatorOverrideBannerView — 렌더 결과에 토큰 원문이 없다", () => {
  it("token 이 든 주소를 넣어도 DOM 에는 *** 만 남는다", () => {
    const url = "wss://server.solidbob.cloud/call-mediator?token=cga_SECRET123&call_id=demo-1";
    const html = renderToStaticMarkup(
      <CallMediatorOverrideBannerView url={url} onClear={() => {}} />,
    );
    expect(html).not.toContain("cga_SECRET123");
    expect(html).toContain("token=***");
    expect(html).toContain("call_id=demo-1");
  });
});
