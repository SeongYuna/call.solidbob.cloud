import type { ReactElement } from "react";
import {
  LANGUAGE_META,
  type TargetLanguage,
} from "../lib/language/languageMeta";

interface LanguageBadgeProps {
  lang: TargetLanguage;
  /** 국기만. 상담기록 목록용. */
  compact?: boolean;
}

export function LanguageBadge({
  lang,
  compact = false,
}: LanguageBadgeProps): ReactElement {
  const meta = LANGUAGE_META[lang];
  if (compact) {
    return (
      <span
        className="language-badge is-compact"
        title={meta.label}
        aria-label={meta.label}
      >
        <span className="language-badge-flag" aria-hidden="true">
          {meta.flag}
        </span>
      </span>
    );
  }
  return (
    <span
      className="language-badge"
      title={meta.label}
      aria-label={meta.label}
    >
      <span className="language-badge-flag" aria-hidden="true">
        {meta.flag}
      </span>
      <span className="language-badge-code">{lang}</span>
    </span>
  );
}
