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
import { MaskedText, revealSpansFor, type RevealSpan } from "./MaskedText";
import { formatOffsetMs } from "../lib/text/codepoints";
import { formatCallStartedAt } from "../lib/formatCallTime";
import { findMatches, type CharRange } from "../lib/text/highlight";
import { ManualSearchBar } from "./ManualSearchBar";
import { ComplianceWarningBanner } from "./ComplianceWarningBanner";
import { CustomerRiskBanner } from "./CustomerRiskBanner";
import { LanguageBadge } from "./LanguageBadge";
import { detectComplianceRisk } from "../lib/compliance/detectComplianceRisk";
import { detectCustomerRisk } from "../lib/customerRisk/detectCustomerRisk";
import type { BannerRiskMatch } from "../lib/customerRisk/detectCustomerRisk";
import type { CustomerRiskMatch } from "../lib/customerRisk/detectCustomerRisk";
import { targetLanguageFromCode } from "../lib/language/languageMeta";
import {
  logPlainReveal,
  maskSensitiveText,
  sensitiveRanges,
} from "../lib/customerRisk/maskSensitiveText";
import {
  logSupervisorAlert,
  type SupervisorAlert,
} from "../lib/customerRisk/supervisorAlert";
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
  onSupervisorAlert?: (alert: SupervisorAlert) => void;
}

const CUSTOMER_GUIDANCE = {
  abuse: "안전 문구 사용을 권장합니다",
  distress: "슈퍼바이저 연결을 고려하세요",
} as const;

function uniqueCustomerBanners(
  risks: readonly CustomerRiskMatch[],
): BannerRiskMatch[] {
  const seen = new Set<"abuse" | "distress">();
  const out: BannerRiskMatch[] = [];
  for (const risk of risks) {
    if (risk.type === "pii" || seen.has(risk.type)) {
      continue;
    }
    seen.add(risk.type);
    out.push(risk as BannerRiskMatch);
  }
  return out;
}

function historyAsUtterance(segment: TranscriptQuerySegment): Utterance {
  return {
    segment_id: String(segment.segment_id),
    speaker: segment.speaker,
    text: segment.text,
    ...(segment.plain_text === undefined
      ? {}
      : { plain_text: segment.plain_text }),
    masked: segment.masked,
    is_final: segment.is_final,
    utterance_end_ms: segment.utterance_end_ms ?? 0,
  };
}

function revealClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function TranscriptPanel({
  onManualSearch,
  onSupervisorAlert = logSupervisorAlert,
}: TranscriptPanelProps): ReactElement {
  const liveUtterances = useCallStore((state) => state.utterances);
  const translations = useCallStore((state) =>
    state.viewMode === "history"
      ? state.historyTranslations
      : state.translations,
  );
  const agentTts = useCallStore((state) =>
    state.viewMode === "history" ? state.historyAgentTts : state.agentTts,
  );
  const callGuard = useCallStore((state) =>
    state.viewMode === "history" ? state.historyCallGuard : state.callGuard,
  );
  const accentHints = useCallStore((state) =>
    state.viewMode === "history" ? state.historyAccentHints : state.accentHints,
  );
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
  const historyCallId = useCallStore((state) => state.historyCallId);
  const callId = useCallStore((state) => state.callId);
  const targetLanguage = useCallStore((state) =>
    state.viewMode === "history"
      ? state.historyTargetLanguage
      : state.targetLanguage,
  );
  const [dismissed, setDismissed] = useState<ReadonlySet<string>>(new Set());
  const [notifiedKeys, setNotifiedKeys] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const [authorized, setAuthorized] = useState(false);
  const [revealAll, setRevealAll] = useState(false);
  const [openedIds, setOpenedIds] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const notifiedRef = useRef(new Set<string>());
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

  useEffect(() => {
    setDismissed(new Set());
    notifiedRef.current = new Set();
    setNotifiedKeys(new Set());
    setAuthorized(false);
    setRevealAll(false);
    setOpenedIds(new Set());
  }, [callId, historyCallId, viewMode]);

  useEffect(() => {
    if (isHistory) {
      return;
    }
    const fresh: SupervisorAlert[] = [];
    const keys: string[] = [];
    for (const item of utterances) {
      if (item.speaker !== "customer") {
        continue;
      }
      for (const risk of detectCustomerRisk(item.text)) {
        if (risk.type === "pii") {
          continue;
        }
        const key = `${item.segment_id}:${risk.type}:${risk.startIndex}`;
        if (notifiedRef.current.has(key)) {
          continue;
        }
        notifiedRef.current.add(key);
        keys.push(key);
        fresh.push({
          type: risk.type,
          matchedText: risk.matchedText,
          callId: callId ?? "",
          timestamp: Date.now(),
        });
      }
    }
    if (keys.length === 0) {
      return;
    }
    for (const alert of fresh) {
      onSupervisorAlert(alert);
    }
    setNotifiedKeys((current) => {
      const next = new Set(current);
      for (const key of keys) {
        next.add(key);
      }
      return next;
    });
  }, [utterances, isHistory, callId, onSupervisorAlert]);

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
      const translated = translations[item.segment_id]?.translated_text;
      if (translated !== undefined) {
        findMatches(translated, needle).forEach((range) => {
          found.push({ segmentId: `${item.segment_id}::tr`, range });
        });
      }
    });
    return found;
  }, [utterances, needle, translations]);

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

  const allRevealIds = useMemo(() => {
    const ids: string[] = [];
    for (const item of utterances) {
      const customerRisks =
        item.speaker === "customer" ? detectCustomerRisk(item.text) : [];
      const piiMatches = customerRisks.filter((risk) => risk.type === "pii");
      const abuseMatches = customerRisks.filter(
        (risk) => risk.type === "abuse",
      );
      const contractMasked =
        piiMatches.length > 0 || abuseMatches.length > 0
          ? []
          : item.masked;
      for (const span of revealSpansFor(
        item.segment_id,
        contractMasked,
        sensitiveRanges(item.text, piiMatches, "pii"),
        sensitiveRanges(item.text, abuseMatches, "abuse"),
      )) {
        ids.push(span.id);
      }
    }
    return ids;
  }, [utterances]);

  const toggleSpan = useCallback(
    (
      id: string,
      field: string,
      currentlyOpen: boolean,
      clock: string,
    ) => {
      if (!authorized) {
        return;
      }
      if (currentlyOpen) {
        if (revealAll) {
          setRevealAll(false);
          setOpenedIds(new Set(allRevealIds.filter((key) => key !== id)));
        } else {
          setOpenedIds((current) => {
            const next = new Set(current);
            next.delete(id);
            return next;
          });
        }
        return;
      }
      setOpenedIds((current) => {
        const next = new Set(current);
        next.add(id);
        return next;
      });
      logPlainReveal(field, clock, callId ?? historyCallId ?? "");
    },
    [allRevealIds, authorized, callId, historyCallId, revealAll],
  );

  const toggleLineSpans = useCallback(
    (spans: readonly RevealSpan[], clock: string) => {
      if (!authorized || spans.length === 0) {
        return;
      }
      const allOpen =
        revealAll || spans.every((span) => openedIds.has(span.id));
      if (allOpen) {
        const closing = new Set(spans.map((span) => span.id));
        if (revealAll) {
          setRevealAll(false);
          setOpenedIds(
            new Set(allRevealIds.filter((id) => !closing.has(id))),
          );
        } else {
          setOpenedIds((current) => {
            const next = new Set(current);
            for (const span of spans) {
              next.delete(span.id);
            }
            return next;
          });
        }
        return;
      }
      setOpenedIds((current) => {
        const next = new Set(current);
        for (const span of spans) {
          next.add(span.id);
        }
        return next;
      });
      const logId = callId ?? historyCallId ?? "";
      for (const span of spans) {
        if (!openedIds.has(span.id)) {
          logPlainReveal(span.field, clock, logId);
        }
      }
    },
    [
      allRevealIds,
      authorized,
      callId,
      historyCallId,
      openedIds,
      revealAll,
    ],
  );

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
  const scrollSegmentId =
    activeSegmentId === null ? null : activeSegmentId.replace(/::tr$/, "");

  useEffect(() => {
    if (scrollSegmentId === null) {
      return;
    }
    const el = itemRefs.current.get(scrollSegmentId);
    if (el === undefined) {
      return;
    }
    el.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [scrollSegmentId, activeStart]);

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
        <div className="transcript-head-row">
          <h2 id="transcript-heading">실시간 자막</h2>
          <div className="mask-auth-bar">
            <button
              type="button"
              className="mask-auth-btn"
              aria-pressed={authorized}
              onClick={() => {
                setAuthorized(true);
              }}
            >
              권한 확인 (데모)
            </button>
            <button
              type="button"
              className="mask-auth-btn"
              disabled={!authorized}
              aria-pressed={revealAll}
              onClick={() => {
                if (revealAll) {
                  setRevealAll(false);
                  setOpenedIds(new Set());
                  return;
                }
                setRevealAll(true);
              }}
            >
              원문 보기
            </button>
          </div>
        </div>
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
              const guard = callGuard[item.segment_id];
              const hits = hitsBySegment.get(item.segment_id) ?? [];
              const translation = translations[item.segment_id];
              const tts = agentTts[item.segment_id];
              const customerRisks =
                item.speaker === "customer"
                  ? detectCustomerRisk(item.text)
                  : [];
              const piiMatches = customerRisks.filter(
                (risk) => risk.type === "pii",
              );
              const abuseMatches = customerRisks.filter(
                (risk) => risk.type === "abuse",
              );
              const sensitive = maskSensitiveText(item.text, customerRisks);
              const displayText = sensitive.masked;
              const revealPlain = item.plain_text ?? sensitive.plain;
              const piiRanges = sensitiveRanges(item.text, piiMatches, "pii");
              const abuseRanges = sensitiveRanges(
                item.text,
                abuseMatches,
                "abuse",
              );
              const contractMasked =
                piiMatches.length > 0 || abuseMatches.length > 0
                  ? []
                  : item.masked;
              const lineSpans = revealSpansFor(
                item.segment_id,
                contractMasked,
                piiRanges,
                abuseRanges,
              );
              const lineClock = revealClock(item.utterance_end_ms);
              const bannerRisks = uniqueCustomerBanners(customerRisks).filter(
                (risk) =>
                  !dismissed.has(
                    `${item.segment_id}:${risk.type}:${risk.startIndex}`,
                  ),
              );
              const hideLegacyGuard = customerRisks.some(
                (risk) => risk.type === "abuse" || risk.type === "distress",
              );
              const compliance =
                item.speaker === "agent" && !dismissed.has(item.segment_id)
                  ? detectComplianceRisk(item.text)
                  : null;
              const translationHits =
                hitsBySegment.get(`${item.segment_id}::tr`) ?? [];
              const ttsLang =
                tts === undefined
                  ? null
                  : (targetLanguage ?? targetLanguageFromCode(tts.target_lang));
              const lineLang =
                translation === undefined
                  ? null
                  : (targetLanguageFromCode(translation.original_lang) ??
                    targetLanguage);
              const activeHit =
                activeMatch !== null &&
                activeMatch.segmentId === item.segment_id
                  ? activeMatch.range
                  : null;
              const activeTranslationHit =
                activeMatch !== null &&
                activeMatch.segmentId === `${item.segment_id}::tr`
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
                      <span className="speaker-cluster">
                        <span className="speaker">
                          {item.speaker === "customer" ? "고객" : "상담원"}
                        </span>
                        {item.speaker === "agent" && tts !== undefined ? (
                          <span className="tts-sent">
                            <TtsIcon />
                            {ttsLang !== null ? (
                              <LanguageBadge lang={ttsLang} />
                            ) : (
                              tts.target_lang.toUpperCase()
                            )}
                            {tts.status === "sent" ? "전송됨" : "대기"}
                          </span>
                        ) : null}
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
                      {lineLang !== null ? (
                        <LanguageBadge lang={lineLang} />
                      ) : null}
                      {accentHints[item.segment_id] === true &&
                      translation === undefined ? (
                        <span className="accent-badge">억양 인식</span>
                      ) : null}
                      <div
                        className={`utterance-bubble${piiMatches.length > 0 ? " has-pii-lock" : ""}${abuseMatches.length > 0 ? " has-abuse-lock" : ""}`}
                      >
                        {abuseMatches.length > 0 ? (
                          <span
                            className="abuse-lock"
                            title="부적절한 표현이 마스킹되었습니다"
                            aria-label="부적절한 표현이 마스킹되었습니다"
                          >
                            <AbuseMaskIcon />
                          </span>
                        ) : null}
                        {piiMatches.length > 0 ? (
                          <span
                            className="pii-lock"
                            title="민감정보가 마스킹되었습니다"
                            aria-label="민감정보가 마스킹되었습니다"
                          >
                            <LockIcon />
                          </span>
                        ) : null}
                        <p className="utterance-text">
                          <MaskedText
                            text={displayText}
                            plainText={revealPlain}
                            masked={contractMasked}
                            piiRanges={piiRanges}
                            abuseRanges={abuseRanges}
                            hits={hits}
                            activeHit={activeHit}
                            authorized={authorized}
                            revealAll={revealAll}
                            openedIds={openedIds}
                            spanIdPrefix={item.segment_id}
                            onToggle={(id, field, currentlyOpen) => {
                              toggleSpan(
                                id,
                                field,
                                currentlyOpen,
                                lineClock,
                              );
                            }}
                          />
                        </p>
                      </div>
                      {hasAlert ? (
                        <button
                          type="button"
                          className="alert-pill"
                          disabled={!authorized}
                          onClick={() => {
                            toggleLineSpans(lineSpans, lineClock);
                          }}
                        >
                          ⚠ 경고
                        </button>
                      ) : null}
                    </div>
                    {guard !== undefined && !hideLegacyGuard ? (
                      <div className="callguard-row">
                        <span
                          className={`callguard-pill${guard.severity === "high" ? " is-high" : ""}`}
                        >
                          🚫 콜가드
                        </span>
                        <span className="callguard-hint">
                          고객이 흥분한 상태입니다. 안내는 이어가시면 됩니다.
                        </span>
                      </div>
                    ) : null}
                    {translation !== undefined ? (
                      <p className="utterance-translation">
                        <MaskedText
                          text={translation.translated_text}
                          plainText={translation.translated_text}
                          masked={[]}
                          hits={translationHits}
                          activeHit={activeTranslationHit}
                        />
                      </p>
                    ) : null}
                    {bannerRisks.map((risk) => {
                      const key = `${item.segment_id}:${risk.type}:${risk.startIndex}`;
                      return (
                        <CustomerRiskBanner
                          key={key}
                          type={risk.type}
                          matchedText={risk.matchedText}
                          guidance={CUSTOMER_GUIDANCE[risk.type]}
                          supervisorNotified={notifiedKeys.has(key)}
                          emphasized={risk.matchedText.includes("가만 안 둘")}
                          onDismiss={() => {
                            setDismissed((current) => {
                              const next = new Set(current);
                              next.add(key);
                              return next;
                            });
                          }}
                        />
                      );
                    })}
                    {compliance !== null ? (
                      <ComplianceWarningBanner
                        detectedPhrase={compliance.detectedPhrase}
                        suggestedPhrase={compliance.suggestedPhrase}
                        onDismiss={() => {
                          setDismissed((current) => {
                            const next = new Set(current);
                            next.add(item.segment_id);
                            return next;
                          });
                        }}
                      />
                    ) : null}
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

function AbuseMaskIcon(): ReactElement {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3 5 6v6c0 5 3.2 7.8 7 9 3.8-1.2 7-4 7-9V6l-7-3Z" />
      <path d="M9 12h6" />
    </svg>
  );
}

function LockIcon(): ReactElement {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path d="M8 11V8a4 4 0 0 1 8 0v3" />
    </svg>
  );
}

function TtsIcon(): ReactElement {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M2.5 6.2v3.6h2.2L8 13.2V2.8L4.7 6.2H2.5Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <path
        d="M10.2 5.6a3 3 0 0 1 0 4.8"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}
