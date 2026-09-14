import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactElement,
} from "react";
import type { ManualSearchOutcome } from "../hooks/useGatewaySession";

function noticeFor(outcome: ManualSearchOutcome, query: string): string {
  switch (outcome.kind) {
    case "added":
      return `「${query}」 결과 ${outcome.count}건을 아래에 추가했어요.`;
    case "empty":
      return `「${query}」 관련 문서 없음. 검색어를 바꿔 다시 찾아보세요.`;
    case "duplicate":
      return `「${query}」 결과는 이미 패널에 올라와 있어요.`;
    case "error":
      return outcome.message;
  }
}

/**
 * §2.3 B-6 으로 "관련 문서 없음"이 떴을 때 상담원이 직접 찾는 경로.
 * 카드가 있든 없든 항상 열려 있어야 한다 — 자동 추천이 맞았는지는 상담원이 판단한다.
 */
export function ManualSearchBar({
  onSearch,
}: {
  onSearch: (query: string) => Promise<ManualSearchOutcome>;
}): ReactElement {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
    }
  }, [open]);

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length === 0 || busy) {
      return;
    }
    setBusy(true);
    setNotice(null);
    const outcome = await onSearch(trimmed);
    setBusy(false);
    setNotice(noticeFor(outcome, trimmed));
  }

  if (!open) {
    return (
      <div className="manual-search">
        <button
          type="button"
          className="manual-search-open"
          onClick={() => {
            setOpen(true);
          }}
        >
          <SearchIcon />
          관련 문서를 못 찾으셨나요?
          <ChevronRightIcon />
        </button>
      </div>
    );
  }

  return (
    <div className="manual-search">
      <form
        className="manual-search-form"
        onSubmit={(event) => {
          void submit(event);
        }}
      >
        <SearchIcon />
        <input
          ref={inputRef}
          type="text"
          className="manual-search-input"
          placeholder="직접 검색해보세요"
          aria-label="문서 직접 검색"
          value={query}
          disabled={busy}
          onChange={(event) => {
            setQuery(event.target.value);
          }}
        />
        <button
          type="submit"
          className="manual-search-submit"
          disabled={busy || query.trim().length === 0}
        >
          검색
        </button>
        <button
          type="button"
          className="search-clear"
          aria-label="직접 검색 닫기"
          onClick={() => {
            setOpen(false);
            setQuery("");
            setNotice(null);
          }}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <path d="M6 6 18 18M18 6 6 18" />
          </svg>
        </button>
      </form>
      {busy ? (
        <p className="manual-search-note">
          <span className="spinner" aria-hidden="true" />
          검색 중...
        </p>
      ) : notice !== null ? (
        <p className="manual-search-note" role="status">
          {notice}
        </p>
      ) : null}
    </div>
  );
}

function SearchIcon(): ReactElement {
  return (
    <svg
      className="search-icon"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="10.5" cy="10.5" r="6.5" />
      <path d="M15.5 15.5 21 21" />
    </svg>
  );
}

function ChevronRightIcon(): ReactElement {
  return (
    <svg
      className="manual-search-chevron"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M9 6 15 12 9 18" />
    </svg>
  );
}
