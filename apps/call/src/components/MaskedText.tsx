import type { ReactElement } from "react";
import type { MaskedSpan } from "../types/contract";
import { buildTextRuns, type CharRange } from "../lib/text/highlight";

interface MaskedTextProps {
  text: string;
  masked: MaskedSpan[];
  hits?: CharRange[];
  activeHit?: CharRange | null;
  piiRanges?: CharRange[];
  abuseRanges?: CharRange[];
}

/**
 * 받은 글을 그리고, `masked` 구간을 `<mark>` 로 표시한다.
 *
 * ⚠ 2026-10-08(`decisions/326`)로 **실서버가 자막에 원문을 싣는다** — 상담원이 번호를
 * 눈으로 확인해야 하기 때문이다. 그래서 `<mark>` 는 "가려진 자리"가 아니라
 * **"저장할 때 가려질 자리"** 를 뜻한다. 저장(DB)·요약은 서버가 마스킹한 뒤 넣으므로
 * SEC-1("마스킹 전 원문이 DB·로그 어디에도 남지 않는다")은 그대로 성립한다.
 *
 * 원문 보기·권한 확인 토글은 `decisions/408`로 걷은 그대로다(`w7-plaintext-reveal-sec1`) —
 * 그때 걷은 이유는 "mock에만 있던 토글이 운영에서도 되는 것처럼 읽힌다"였고, 지금은
 * 토글 없이 처음부터 보인다.
 *
 * mock 모드는 다르다 — `isCoreApiConfigured()` 가 거짓이면 화면이 스스로 가려
 * `is-pii`/`is-abuse` 구간을 만든다. 그쪽은 여전히 "이미 가려진 자리"다.
 */
export function MaskedText({
  text,
  masked,
  hits = [],
  activeHit = null,
  piiRanges = [],
  abuseRanges = [],
}: MaskedTextProps): ReactElement {
  if (
    masked.length === 0 &&
    hits.length === 0 &&
    piiRanges.length === 0 &&
    abuseRanges.length === 0
  ) {
    return <span>{text}</span>;
  }

  const runs = buildTextRuns(text, masked, hits, activeHit, {
    pii: piiRanges,
    abuse: abuseRanges,
  });

  return (
    <>
      {runs.map((run, index) => {
        if (!run.masked && !run.hit) {
          return <span key={index}>{run.text}</span>;
        }
        const classes = [
          run.maskKind === "abuse"
            ? "masked-span is-abuse"
            : run.maskKind === "pii"
              ? "masked-span is-pii"
              : run.masked
                ? "masked-span"
                : "",
          run.hit ? "search-hit" : "",
          run.active ? "is-active" : "",
        ]
          .filter((name) => name.length > 0)
          .join(" ");
        return (
          <mark key={index} className={classes}>
            {run.text}
          </mark>
        );
      })}
    </>
  );
}
