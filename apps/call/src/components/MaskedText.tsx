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
 * 마스킹본을 그대로 그린다 — 원문 보기·권한 확인 토글은 `decisions/408`로 걷었다
 * (`w7-plaintext-reveal-sec1`). SEC-1("마스킹 전 원문이 DB·로그 어디에도 남지 않는다")과
 * "권한 확인 후 원문 열람"은 동시에 성립하지 않는다 — 원문을 보여주려면 원문이 어딘가
 * 있어야 하는데, 실서버는 원문을 절대 주지 않는다(줄 수 없다). mock에만 있던 토글이라
 * 시연에서 "운영에서도 원문을 볼 수 있다"로 잘못 읽힐 위험이 있었다.
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
