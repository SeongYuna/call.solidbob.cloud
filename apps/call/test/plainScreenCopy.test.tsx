// Requirement: C-5, SEC-1, QUA-1
/**
 * `decisions/326` — 상담원 화면은 **원문**, 저장은 마스킹본.
 *
 * 2026-10-08 운영 배포(server 0.1.49 · call-mediator 0.2.16)로 `/ws` 자막이 원문이 됐다.
 * 그런데 화면 문구·색은 「이미 가려진 자막」을 전제로 쓰여 있었다 — 원문이 보이는데
 * 「민감정보가 마스킹되었습니다」가 뜨고, 고객이 번호를 불렀을 뿐인 줄에 상담원 위반과
 * 같은 빨간 **「⚠ 경고」** 가 붙었다(시연 영상 검토 2026-10-02 지적 ③).
 *
 * 이 테스트는 **되돌아가는 것을 막는다**. 문구는 소스에서 직접 읽어 대조한다 —
 * 손으로 적어 둔 목록끼리 맞추면 또 갈라진다(`ai` 쪽에서 09-22 에 실제로 겪었다).
 */
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MaskedText } from "../src/components/MaskedText";
import type { MaskedSpan } from "../src/types/contract";

const PANEL = readFileSync(new URL("../src/components/TranscriptPanel.tsx", import.meta.url), "utf8");
const MASKED = readFileSync(new URL("../src/components/MaskedText.tsx", import.meta.url), "utf8");

describe("decisions/326 — 화면은 원문, 표시는 「저장 시 가림」", () => {
  it("원문을 그대로 그리고 개인정보 구간만 <mark> 로 감싼다", () => {
    const text = "제 번호는 010-9876-5432 이에요";
    const masked: MaskedSpan[] = [{ type: "P4", span: [6, 19] }];
    const html = renderToStaticMarkup(<MaskedText text={text} masked={masked} />);

    // 상담원이 번호를 눈으로 확인해야 하므로 원문이 보여야 한다.
    expect(html).toContain("010-9876-5432");
    // 그 자리는 「저장할 때 가려질 자리」로 표시된다.
    expect(html).toContain('<mark class="masked-span">010-9876-5432</mark>');
    // 별 표시로 덮지 않는다 — 덮으면 326 이전으로 되돌아간 것이다.
    expect(html).not.toContain("*");
  });

  it("개인정보 구간이 없으면 아무것도 감싸지 않는다", () => {
    const html = renderToStaticMarkup(<MaskedText text="안녕하세요 다산콜센터입니다" masked={[]} />);
    expect(html).not.toContain("<mark");
  });

  it("옛 문구가 되살아나지 않는다 — 원문이 보이는데 「마스킹되었습니다」는 거짓이다", () => {
    expect(PANEL).not.toContain("민감정보가 마스킹되었습니다");
    expect(PANEL).toContain("저장할 때 가려지는 부분입니다");
  });

  it("개인정보 줄에 상담원 위반과 같은 「⚠ 경고」를 붙이지 않는다", () => {
    // 고객이 번호를 불렀을 뿐인 줄이다 — 빨간 경고는 「고객이 잘못했다」로 읽힌다.
    expect(PANEL).not.toContain('className="alert-pill">⚠ 경고');
    expect(PANEL).toContain("저장 시 가림");
    expect(PANEL).toContain('className="alert-pill is-mask"');
  });

  it("「실서버는 원문을 절대 주지 않는다」는 주석이 남아 있지 않다", () => {
    expect(MASKED).not.toContain("실서버는 원문을 절대 주지 않는다");
    expect(MASKED).toContain("decisions/326");
  });
});
