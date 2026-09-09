/**
 * C-1~C-4 mock. 상담원 발화 텍스트만 본다.
 * 배열 매칭은 자리표시자다. 실제 분류기가 오면 이 함수만 갈아끼운다.
 */
export interface ComplianceRisk {
  detectedPhrase: string;
  suggestedPhrase: string;
}

const RULES: readonly ComplianceRisk[] = [
  { detectedPhrase: "불법체류", suggestedPhrase: "체류기간 경과" },
];

export function detectComplianceRisk(text: string): ComplianceRisk | null {
  for (const rule of RULES) {
    if (text.includes(rule.detectedPhrase)) {
      return rule;
    }
  }
  return null;
}
