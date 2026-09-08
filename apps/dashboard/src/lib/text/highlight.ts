import type { MaskedSpan } from "../../types/contract";

/** 코드포인트 오프셋 기준 반열린 구간 [start, end). 마스킹 span 과 같은 단위다. */
export interface CharRange {
  start: number;
  end: number;
}

export type DisplayMaskKind = "contract" | "pii" | "abuse";

export interface TextRun {
  text: string;
  masked: boolean;
  maskKind: DisplayMaskKind | null;
  hit: boolean;
  active: boolean;
}

/**
 * 대소문자를 무시하고 겹치지 않는 일치 구간을 찾는다.
 * 마스킹 span 이 코드포인트 기준(7.3절 v2)이라 여기서도 같은 단위를 쓴다.
 */
export function findMatches(text: string, query: string): CharRange[] {
  const chars = Array.from(text);
  const needle = Array.from(query);
  if (needle.length === 0 || needle.length > chars.length) {
    return [];
  }

  const found: CharRange[] = [];
  const limit = chars.length - needle.length;
  for (let i = 0; i <= limit; i += 1) {
    let matched = true;
    for (let j = 0; j < needle.length; j += 1) {
      if (chars[i + j].toLowerCase() !== needle[j].toLowerCase()) {
        matched = false;
        break;
      }
    }
    if (matched) {
      found.push({ start: i, end: i + needle.length });
      i += needle.length - 1;
    }
  }
  return found;
}

function mark(flags: Uint8Array, range: CharRange): void {
  const start = Math.max(0, range.start);
  const end = Math.min(flags.length, range.end);
  for (let i = start; i < end; i += 1) {
    flags[i] = 1;
  }
}

/**
 * 마스킹과 검색 일치는 서로 겹칠 수 있으므로 구간을 잘라 붙이지 않고
 * 코드포인트마다 표시를 남긴 뒤 같은 표시끼리 묶는다.
 */
export function buildTextRuns(
  text: string,
  masked: MaskedSpan[],
  hits: CharRange[],
  activeHit: CharRange | null,
  displayMasks: {
    pii?: readonly CharRange[];
    abuse?: readonly CharRange[];
  } = {},
): TextRun[] {
  const chars = Array.from(text);
  const contractFlags = new Uint8Array(chars.length);
  const piiFlags = new Uint8Array(chars.length);
  const abuseFlags = new Uint8Array(chars.length);
  const hitFlags = new Uint8Array(chars.length);
  const activeFlags = new Uint8Array(chars.length);

  masked.forEach((span) => {
    mark(contractFlags, { start: span.span[0], end: span.span[1] });
  });
  (displayMasks.pii ?? []).forEach((range) => {
    mark(piiFlags, range);
  });
  (displayMasks.abuse ?? []).forEach((range) => {
    mark(abuseFlags, range);
  });
  hits.forEach((range) => {
    mark(hitFlags, range);
  });
  if (activeHit !== null) {
    mark(activeFlags, activeHit);
  }

  function kindAt(index: number): DisplayMaskKind | null {
    if (abuseFlags[index] === 1) {
      return "abuse";
    }
    if (piiFlags[index] === 1) {
      return "pii";
    }
    if (contractFlags[index] === 1) {
      return "contract";
    }
    return null;
  }

  const runs: TextRun[] = [];
  let cursor = 0;
  while (cursor < chars.length) {
    const maskKind = kindAt(cursor);
    const isHit = hitFlags[cursor] === 1;
    const isActive = activeFlags[cursor] === 1;
    let end = cursor + 1;
    while (
      end < chars.length &&
      kindAt(end) === maskKind &&
      (hitFlags[end] === 1) === isHit &&
      (activeFlags[end] === 1) === isActive
    ) {
      end += 1;
    }
    runs.push({
      text: chars.slice(cursor, end).join(""),
      masked: maskKind !== null,
      maskKind,
      hit: isHit,
      active: isActive,
    });
    cursor = end;
  }
  return runs;
}
