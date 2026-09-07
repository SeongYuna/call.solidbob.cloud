/**
 * C-6 mock. 고객 발화 텍스트만 본다.
 * 키워드·정규식은 자리표시자다. 실제 모델이 오면 이 함수만 갈아끼운다.
 */
export type CustomerRiskType = "abuse" | "distress" | "pii";

export interface CustomerRiskMatch {
  type: CustomerRiskType;
  matchedText: string;
  startIndex: number;
  endIndex: number;
}

export type BannerRiskMatch = CustomerRiskMatch & {
  type: "abuse" | "distress";
};

/** 지원금 지연 시나리오 00:28 원문 한 조각. 같은 글자를 감지 키워드로 쓴다. */
const GRANT_ABUSE_TAIL = "짜증나 죽겠네";

const ABUSE = [
  "미친 거 아니에요",
  "이름 뭐예요",
  "개판",
  "가만 안 둘",
  "가만 안 둔다",
  "죽여버린다",
  GRANT_ABUSE_TAIL,
  "짜증나",
  GRANT_ABUSE_TAIL.slice(GRANT_ABUSE_TAIL.lastIndexOf(" ") + 1),
] as const;
const DISTRESS = ["너무 힘들어요", "죽고 싶어요"] as const;
const PII_RRN = /\d{6}-\d{7}/g;

function isBoundaryMark(ch: string): boolean {
  return /\s/u.test(ch) || /\p{P}/u.test(ch) || /\p{S}/u.test(ch);
}

/** 문장부호·공백은 매칭 구간 밖으로 밀어 별표에 섞이지 않게 한다. */
function tightenSpan(
  text: string,
  start: number,
  end: number,
): { startIndex: number; endIndex: number; matchedText: string } | null {
  const chars = [...text.slice(start, end)];
  let from = 0;
  let to = chars.length;
  while (from < to && isBoundaryMark(chars[from])) {
    from += 1;
  }
  while (to > from && isBoundaryMark(chars[to - 1])) {
    to -= 1;
  }
  if (from >= to) {
    return null;
  }
  const head = chars.slice(0, from).join("");
  const body = chars.slice(from, to).join("");
  const startIndex = start + head.length;
  return {
    startIndex,
    endIndex: startIndex + body.length,
    matchedText: body,
  };
}

function collectPhrases(
  text: string,
  type: CustomerRiskType,
  phrases: readonly string[],
): CustomerRiskMatch[] {
  const found: CustomerRiskMatch[] = [];
  const ordered = [...phrases].sort((a, b) => b.length - a.length);
  for (const phrase of ordered) {
    let from = 0;
    while (from <= text.length) {
      const startIndex = text.indexOf(phrase, from);
      if (startIndex === -1) {
        break;
      }
      const rawEnd = startIndex + phrase.length;
      const overlap = found.some(
        (item) => startIndex < item.endIndex && rawEnd > item.startIndex,
      );
      if (overlap) {
        from = rawEnd;
        continue;
      }
      const tight = tightenSpan(text, startIndex, rawEnd);
      if (tight !== null) {
        found.push({
          type,
          matchedText: tight.matchedText,
          startIndex: tight.startIndex,
          endIndex: tight.endIndex,
        });
      }
      from = rawEnd;
    }
  }
  return found;
}

export function detectCustomerRisk(text: string): CustomerRiskMatch[] {
  const pii: CustomerRiskMatch[] = [];
  for (const hit of text.matchAll(PII_RRN)) {
    const startIndex = hit.index ?? 0;
    const matchedText = hit[0];
    pii.push({
      type: "pii",
      matchedText,
      startIndex,
      endIndex: startIndex + matchedText.length,
    });
  }
  return [
    ...collectPhrases(text, "abuse", ABUSE),
    ...collectPhrases(text, "distress", DISTRESS),
    ...pii,
  ];
}
