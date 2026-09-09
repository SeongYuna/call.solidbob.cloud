/**
 * A-5 화면용 언어 코드. §7.3 계약에는 아직 없다.
 * TranslatedUtterance.original_lang 은 소문자, 통화 설정은 대문자다.
 */
export type TargetLanguage = "VI" | "EN" | "JA" | "ZH" | "TH";

export interface LanguageMeta {
  label: string;
  flag: string;
  originalLang: "vi" | "en" | "ja" | "zh" | "th";
}

export const LANGUAGE_META: Record<TargetLanguage, LanguageMeta> = {
  VI: { label: "베트남어", flag: "🇻🇳", originalLang: "vi" },
  EN: { label: "영어", flag: "🇺🇸", originalLang: "en" },
  JA: { label: "일본어", flag: "🇯🇵", originalLang: "ja" },
  ZH: { label: "중국어", flag: "🇨🇳", originalLang: "zh" },
  TH: { label: "태국어", flag: "🇹🇭", originalLang: "th" },
};

export const TARGET_LANGUAGES: readonly TargetLanguage[] = [
  "VI",
  "EN",
  "JA",
  "ZH",
  "TH",
];

export function targetLanguageFromCode(
  code: string | undefined,
): TargetLanguage | null {
  if (code === undefined || code.length === 0) {
    return null;
  }
  const upper = code.toUpperCase();
  if (upper in LANGUAGE_META) {
    return upper as TargetLanguage;
  }
  return null;
}
