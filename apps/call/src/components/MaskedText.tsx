import type { ReactElement } from "react";
import type { MaskedSpan, MaskType } from "../types/contract";
import { sliceByCodepoints } from "../lib/text/codepoints";
import {
  buildTextRuns,
  type CharRange,
} from "../lib/text/highlight";

const FIELD_BY_MASK: Record<MaskType, string> = {
  P1: "주민번호",
  P2: "카드번호",
  P3: "계좌",
  P4: "연락처",
  P5: "이메일",
  P6: "이름",
  P7: "주소",
};

export interface RevealSpan {
  id: string;
  field: string;
  range: CharRange;
}

interface MaskedTextProps {
  text: string;
  plainText: string;
  masked: MaskedSpan[];
  hits?: CharRange[];
  activeHit?: CharRange | null;
  piiRanges?: CharRange[];
  abuseRanges?: CharRange[];
  authorized?: boolean;
  revealAll?: boolean;
  openedIds?: ReadonlySet<string>;
  spanIdPrefix?: string;
  onToggle?: (id: string, field: string, currentlyOpen: boolean) => void;
}

export function revealSpansFor(
  prefix: string,
  masked: MaskedSpan[],
  piiRanges: readonly CharRange[],
  abuseRanges: readonly CharRange[],
): RevealSpan[] {
  const spans: RevealSpan[] = [];
  masked.forEach((span, index) => {
    spans.push({
      id: `${prefix}:c:${index}`,
      field: FIELD_BY_MASK[span.type],
      range: { start: span.span[0], end: span.span[1] },
    });
  });
  piiRanges.forEach((range, index) => {
    spans.push({
      id: `${prefix}:p:${index}`,
      field: "개인정보",
      range,
    });
  });
  abuseRanges.forEach((range, index) => {
    spans.push({
      id: `${prefix}:a:${index}`,
      field: "부적절한 표현",
      range,
    });
  });
  return spans;
}

function coveringSpan(
  spans: readonly RevealSpan[],
  start: number,
  end: number,
): RevealSpan | null {
  return (
    spans.find(
      (span) => start >= span.range.start && end <= span.range.end,
    ) ?? null
  );
}

export function MaskedText({
  text,
  plainText,
  masked,
  hits = [],
  activeHit = null,
  piiRanges = [],
  abuseRanges = [],
  authorized = false,
  revealAll = false,
  openedIds = new Set(),
  spanIdPrefix = "",
  onToggle,
}: MaskedTextProps): ReactElement {
  const revealSpans = revealSpansFor(
    spanIdPrefix,
    masked,
    piiRanges,
    abuseRanges,
  );
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

  let cursor = 0;
  return (
    <>
      {runs.map((run, index) => {
        const start = cursor;
        const end = cursor + Array.from(run.text).length;
        cursor = end;
        if (!run.masked && !run.hit) {
          return <span key={index}>{run.text}</span>;
        }
        const cover = run.masked ? coveringSpan(revealSpans, start, end) : null;
        const open =
          cover !== null &&
          authorized &&
          (revealAll || openedIds.has(cover.id));
        const shown =
          open && cover !== null
            ? sliceByCodepoints(plainText, start, end)
            : run.text;
        const classes = [
          run.maskKind === "abuse"
            ? "masked-span is-abuse"
            : run.maskKind === "pii"
              ? "masked-span is-pii"
              : run.masked
                ? "masked-span"
                : "",
          open ? "is-revealed" : "",
          authorized && cover !== null ? "is-clickable" : "",
          run.hit ? "search-hit" : "",
          run.active ? "is-active" : "",
        ]
          .filter((name) => name.length > 0)
          .join(" ");
        if (!authorized || cover === null || onToggle === undefined) {
          return (
            <mark key={index} className={classes}>
              {shown}
            </mark>
          );
        }
        return (
          <button
            key={index}
            type="button"
            className={`${classes} masked-span-btn`}
            data-mask-span={cover.id}
            data-mask-open={open ? "true" : "false"}
            aria-pressed={open}
            aria-label={`${cover.field}${open ? " 원문" : " 마스킹"} 열람 전환`}
            onClick={() => {
              onToggle(cover.id, cover.field, open);
            }}
          >
            {shown}
          </button>
        );
      })}
    </>
  );
}
