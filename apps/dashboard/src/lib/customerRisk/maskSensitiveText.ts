import type { CustomerRiskMatch } from "./detectCustomerRisk";
import type { CharRange } from "../text/highlight";

function utf16ToCodeRange(
  text: string,
  start: number,
  end: number,
): CharRange {
  const from = Array.from(text.slice(0, start)).length;
  const width = Array.from(text.slice(start, end)).length;
  return { start: from, end: from + width };
}

function maskPiiSlice(slice: string): string {
  const dash = slice.indexOf("-");
  if (dash === -1) {
    return "•".repeat([...slice].length);
  }
  return `${slice.slice(0, dash + 1)}${"•".repeat([...slice.slice(dash + 1)].length)}`;
}

function isAbuseLetter(ch: string): boolean {
  return /\p{L}|\p{N}/u.test(ch);
}

/** 글자만 * 로 바꾸고 공백·문장부호는 원위치 그대로 둔다. */
function maskAbuseSlice(slice: string): string {
  return [...slice].map((ch) => (isAbuseLetter(ch) ? "*" : ch)).join("");
}

export interface SensitiveMaskResult {
  masked: string;
  plain: string;
  onReveal: (field: string, clock: string, callId: string) => void;
}

/**
 * PII는 •, 욕설은 * 로 같은 길이를 유지해 구간이 어긋나지 않게 한다.
 * 기본 화면은 마스킹본이다. 권한 확인 후에는 예외적으로 원문(plain)을
 * 임시 노출할 수 있다.
 */
export function maskSensitiveText(
  text: string,
  matches: readonly CustomerRiskMatch[],
): SensitiveMaskResult {
  const hits = [...matches]
    .filter((item) => item.type === "pii" || item.type === "abuse")
    .sort((a, b) => b.startIndex - a.startIndex);
  let next = text;
  for (const hit of hits) {
    const slice = next.slice(hit.startIndex, hit.endIndex);
    const masked =
      hit.type === "pii" ? maskPiiSlice(slice) : maskAbuseSlice(slice);
    next = `${next.slice(0, hit.startIndex)}${masked}${next.slice(hit.endIndex)}`;
  }
  return { masked: next, plain: text, onReveal: logPlainReveal };
}

export function logPlainReveal(
  field: string,
  clock: string,
  callId: string,
): void {
  console.info(
    `[열람 기록] ${field} 필드 열람 - ${clock} 시점, ${callId}`,
  );
}

export function sensitiveRanges(
  text: string,
  matches: readonly CustomerRiskMatch[],
  type: "pii" | "abuse",
): CharRange[] {
  return matches
    .filter((item) => item.type === type)
    .map((item) => utf16ToCodeRange(text, item.startIndex, item.endIndex));
}
