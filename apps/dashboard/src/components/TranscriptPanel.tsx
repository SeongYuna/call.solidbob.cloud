import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactElement,
  type UIEvent,
} from "react";
import { BrandLockup } from "./AppHeader";
import { MaskedText } from "./MaskedText";
import { formatOffsetMs } from "../lib/text/codepoints";
import { formatCallStartedAt } from "../lib/formatCallTime";
import { findMatches, type CharRange } from "../lib/text/highlight";
import { ManualSearchBar } from "./ManualSearchBar";
import type { ManualSearchOutcome } from "../hooks/useGatewaySession";
import { useCallStore, type Utterance } from "../store/callStore";
import type { TranscriptQuerySegment } from "../types/contract";

/** 이 거리 안이면 맨 아래에 있는 것으로 본다. */
const PIN_THRESHOLD_PX = 80;
const SMOOTH_LOCK_MS = 420;

interface SearchMatch {
  segmentId: string;
  range: CharRange;
}

interface TranscriptPanelProps {
  onManualSearch: (query: string) => Promise<ManualSearchOutcome>;
}

function historyAsUtterance(segment: TranscriptQuerySegment): Utterance {
  return {
    segment_id: String(segment.segment_id),
    speaker: segment.speaker,
    text: segment.text,
    masked: segment.masked,
    is_final: segment.is_final,
    utterance_end_ms: segment.utterance_end_ms ?? 0,
  };
}

export function TranscriptPanel({
  onManualSearch,
}: TranscriptPanelProps): ReactElement {
  const liveUtterances = useCallStore((state) => state.utterances);
  const viewMode = useCallStore((state) => state.viewMode);
  const historySegments = useCallStore((state) => state.historySegments);
  const historyStartedAt = useCallStore((state) => state.historyStartedAt);
  const resumeLive = useCallStore((state) => state.resumeLive);
  const isHistory = viewMode === "history";
  const utterances = useMemo(
    () =>
      isHistory
        ? historySegments.map(historyAsUtterance)
        : liveUtterances,
    [isHistory, historySegments, liveUtterances],
  );
  const prevModeRef = useRef(viewMode);

  const bodyRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef(new Map<string, HTMLLIElement>());
  const pinnedRef = useRef(true);
  const autoScrollingRef = useRef(false);
  const unlockRef = useRef<number | null>(null);

  const [showJump, setShowJump] = useState(false);
  const [query, setQuery] = useState("");
  const [hitIndex, setHitIndex] = useState(0);

  useEffect(() => {
    if (prevModeRef.current === "history" && viewMode === "live") {
      pinnedRef.current = true;
      setShowJump(false);
    }
    prevModeRef.current = viewMode;
  }, [viewMode]);

  const needle = query.trim();

  const matches = useMemo<SearchMatch[]>(() => {
    if (needle.length === 0) {
      return [];
    }
    const found: SearchMatch[] = [];
    utterances.forEach((item) => {
      findMatches(item.text, needle).forEach((range) => {
        found.push({ segmentId: item.segment_id, range });
      });
    });
    return found;
  }, [utterances, needle]);

  const hitsBySegment = useMemo(() => {
    const grouped = new Map<string, CharRange[]>();
    matches.forEach((match) => {
      const list = grouped.get(match.segmentId);
      if (list === undefined) {
        grouped.set(match.segmentId, [match.range]);
      } else {
        list.push(match.range);
      }
    });
    return grouped;
  }, [matches]);

  const total = matches.length;
  const current = total === 0 ? -1 : Math.min(hitIndex, total - 1);
  const activeMatch = current === -1 ? null : matches[current];

  const scrollToBottom = useCallback((smooth: boolean): void => {
    const el = bodyRef.current;
    if (el === null) {
      return;
    }
    autoScrollingRef.current = true;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });

    if (unlockRef.current !== null) {
      window.clearTimeout(unlockRef.current);
    }
    unlockRef.current = window.setTimeout(
      () => {
        unlockRef.current = null;
        autoScrollingRef.current = false;
        const settled = bodyRef.current;
        if (settled === null) {
          return;
        }
        const distance =
          settled.scrollHeight - settled.scrollTop - settled.clientHeight;
        if (distance <= PIN_THRESHOLD_PX) {
          pinnedRef.current = true;
          setShowJump(false);
        }
      },
      smooth ? SMOOTH_LOCK_MS : 0,
    );
  }, []);

  useEffect(() => {
    return () => {
      if (unlockRef.current !== null) {
        window.clearTimeout(unlockRef.current);
      }
    };
  }, []);

  function onBodyScroll(event: UIEvent<HTMLDivElement>): void {
    if (autoScrollingRef.current) {
      return;
    }
    const el = event.currentTarget;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    const atBottom = distance <= PIN_THRESHOLD_PX;
    pinnedRef.current = atBottom;
    if (atBottom) {
      setShowJump(false);
    }
  }

  useEffect(() => {
    if (isHistory) {
      setShowJump(false);
      pinnedRef.current = false;
      const el = bodyRef.current;
      if (el !== null) {
        el.scrollTop = 0;
      }
      return;
    }
    if (utterances.length === 0) {
      pinnedRef.current = true;
      setShowJump(false);
      return;
    }
    // 위로 올려 과거 대화를 보는 중이면 끌어내리지 않고 알림만 띄운다.
    if (!pinnedRef.current) {
      setShowJump(true);
      return;
    }
    const last = utterances[utterances.length - 1];
    if (last === undefined) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      scrollToBottom(last.is_final);
    });
    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [isHistory, utterances, scrollToBottom]);

  function jumpToLatest(): void {
    pinnedRef.current = true;
    setShowJump(false);
    scrollToBottom(true);
  }

  useEffect(() => {
    setHitIndex(0);
  }, [needle]);

  const activeSegmentId = activeMatch === null ? null : activeMatch.segmentId;
  const activeStart = activeMatch === null ? -1 : activeMatch.range.start;

  useEffect(() => {
    if (activeSegmentId === null) {
      return;
    }
    const el = itemRefs.current.get(activeSegmentId);
    if (el === undefined) {
      return;
    }
    el.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [activeSegmentId, activeStart]);

  function stepHit(delta: number): void {
    if (total === 0) {
      return;
    }
    setHitIndex((((current + delta) % total) + total) % total);
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>): void {
    if (event.key === "Enter") {
      event.preventDefault();
      stepHit(event.shiftKey ? -1 : 1);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      setQuery("");
    }
  }

  return (
    <section
      className="panel transcript-panel"
      aria-labelledby="transcript-heading"
    >
      <header className="pane-header left-pane-header">
        <BrandLockup />
      </header>
      {isHistory && historyStartedAt !== null ? (
        <div className="history-banner" role="status">
          <span>
            지난 통화 보는 중 · {formatCallStartedAt(historyStartedAt)}
          </span>
          <button type="button" className="history-banner-back" onClick={resumeLive}>
            실시간으로 돌아가기
          </button>
        </div>
      ) : null}
      <header className="panel-head transcript-head">
        <h2 id="transcript-heading">실시간 자막</h2>
        <div className="transcript-search">
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
          <input
            type="text"
            className="search-input"
            placeholder="자막 검색"
            aria-label="자막 검색"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
            }}
            onKeyDown={onSearchKeyDown}
          />
          {needle.length > 0 ? (
            <div className="search-nav">
              <span className="search-count" aria-live="polite">
                {current + 1} / 총 {total}
              </span>
              <button
                type="button"
                className="search-step"
                onClick={() => {
                  stepHit(-1);
                }}
                disabled={total === 0}
                aria-label="이전 검색 결과"
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="m6 15 6-6 6 6" />
                </svg>
              </button>
              <button
                type="button"
                className="search-step"
                onClick={() => {
                  stepHit(1);
                }}
                disabled={total === 0}
                aria-label="다음 검색 결과"
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </button>
              <button
                type="button"
                className="search-clear"
                onClick={() => {
                  setQuery("");
                }}
                aria-label="검색어 지우기"
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
            </div>
          ) : null}
        </div>
      </header>

      <div className="panel-body" ref={bodyRef} onScroll={onBodyScroll}>
        {utterances.length === 0 ? (
          <p className="empty">발화가 아직 없습니다.</p>
        ) : (
          <ol className="utterance-list">
            {utterances.map((item) => {
              const hasAlert = item.masked.length > 0;
              const hits = hitsBySegment.get(item.segment_id) ?? [];
              const activeHit =
                activeMatch !== null &&
                activeMatch.segmentId === item.segment_id
                  ? activeMatch.range
                  : null;
              return (
                <li
                  key={item.segment_id}
                  ref={(node) => {
                    if (node === null) {
                      itemRefs.current.delete(item.segment_id);
                    } else {
                      itemRefs.current.set(item.segment_id, node);
                    }
                  }}
                  className={`utterance ${item.speaker}${item.is_final ? "" : " interim"}`}
                >
                  <span className="bar" aria-hidden="true" />
                  <div className="utterance-body">
                    <div className="utterance-meta">
                      <span className="speaker">
                        {item.speaker === "customer" ? "고객" : "상담원"}
                      </span>
                      {!isHistory || item.utterance_end_ms > 0 ? (
                        <time
                          className="ts"
                          dateTime={`+${item.utterance_end_ms}ms`}
                        >
                          {formatOffsetMs(item.utterance_end_ms)}
                        </time>
                      ) : null}
                    </div>
                    <div className="utterance-line">
                      <p className="utterance-text">
                        <MaskedText
                          text={item.text}
                          masked={item.masked}
                          hits={hits}
                          activeHit={activeHit}
                        />
                      </p>
                      {hasAlert ? (
                        <span className="alert-pill">⚠ 경고</span>
                      ) : null}
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      <ManualSearchBar onSearch={onManualSearch} />

      {showJump && !isHistory ? (
        <button type="button" className="jump-latest" onClick={jumpToLatest}>
          <svg
            className="jump-latest-icon"
            width="13"
            height="13"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M12 5v14M6 13l6 6 6-6" />
          </svg>
          최신 대화로 이동
        </button>
      ) : null}
    </section>
  );
}
