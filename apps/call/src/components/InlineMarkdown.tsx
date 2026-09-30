import { Fragment, type ReactElement } from "react";

/**
 * 카드 요약에 섞여 오는 최소한의 마크다운(`**굵게**`·`` `코드` ``)을 그린다. 지식베이스 청크가
 * 마크다운 원문이라 `**` 가 글자 그대로 보였다(QA 2회차 관찰). 그 둘만 다루고 나머지는 글자 그대로 둔다 —
 * HTML 을 만들지 않으므로 주입 여지가 없다.
 */
export function InlineMarkdown({ text }: { text: string }): ReactElement {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter((p) => p.length > 0);
  return (
    <>
      {parts.map((part, index) => {
        if (part.length > 4 && part.startsWith("**") && part.endsWith("**")) {
          return <strong key={index}>{part.slice(2, -2)}</strong>;
        }
        if (part.length > 2 && part.startsWith("`") && part.endsWith("`")) {
          return <code key={index}>{part.slice(1, -1)}</code>;
        }
        return <Fragment key={index}>{part}</Fragment>;
      })}
    </>
  );
}
