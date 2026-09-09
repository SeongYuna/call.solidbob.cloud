import { useEffect, useMemo, useState, type ReactElement, type ReactNode } from "react";
import type { CallWrapUp, SentimentSummary } from "../types/contract";
import { getHistoryPlayback } from "../lib/api/coreClient";
import { DEFAULT_LOCAL_RESOURCES } from "../mock/localResources";
import { cardId, useCallStore, type Utterance } from "../store/callStore";
import { BlacklistRequestButton } from "./BlacklistRequestButton";
import { FollowUpChecklist } from "./FollowUpChecklist";
import { LocalResourceCard } from "./LocalResourceCard";

export interface CallSummaryModel {
  callId: string;
  summary: string;
  tags: readonly string[];
  followUps: readonly string[];
  resources: CallWrapUp["local_resources"];
  sentiment?: SentimentSummary;
}

interface CallSummaryPanelProps {
  call: CallSummaryModel;
  onClose: () => void;
  onStartNewCall: () => void;
}

export function callSummaryFromWrapUp(wrapUp: CallWrapUp): CallSummaryModel {
  return {
    callId: wrapUp.call_id,
    summary: wrapUp.summary.join(" "),
    tags:
      wrapUp.tags !== undefined && wrapUp.tags.length > 0
        ? wrapUp.tags
        : [wrapUp.category],
    followUps: wrapUp.follow_ups,
    resources:
      wrapUp.local_resources !== undefined && wrapUp.local_resources.length > 0
        ? wrapUp.local_resources
        : [...DEFAULT_LOCAL_RESOURCES],
    sentiment: wrapUp.sentiment,
  };
}

interface CallSummaryHostProps {
  onClose: () => void;
  onStartNewCall: () => void;
  onWrapUp: () => Promise<CallWrapUp>;
}

/** 종료 직후와 상담기록 조회가 같은 화면을 쓴다. */
export function CallSummaryHost({
  onClose,
  onStartNewCall,
  onWrapUp,
}: CallSummaryHostProps): ReactElement {
  const viewMode = useCallStore((state) => state.viewMode);
  const historyCallId = useCallStore((state) => state.historyCallId);
  const [live, setLive] = useState<CallWrapUp | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (viewMode === "history") {
      return;
    }
    let alive = true;
    setLive(null);
    setError(null);
    onWrapUp()
      .then((result) => {
        if (alive) {
          setLive(result);
        }
      })
      .catch((cause: unknown) => {
        if (alive) {
          setError(
            cause instanceof Error
              ? cause.message
              : "통화 후 처리를 불러오지 못했습니다.",
          );
        }
      });
    return () => {
      alive = false;
    };
  }, [onWrapUp, viewMode]);

  if (viewMode === "history") {
    const playback =
      historyCallId === null ? null : getHistoryPlayback(historyCallId);
    if (playback?.wrapUp === undefined) {
      return (
        <CallSummaryShell onClose={onClose} onStartNewCall={onStartNewCall}>
          <section className="wrapup-card">
            <p className="wrapup-error">이 통화의 요약이 없습니다.</p>
          </section>
        </CallSummaryShell>
      );
    }
    return (
      <CallSummaryPanel
        call={callSummaryFromWrapUp(playback.wrapUp)}
        onClose={onClose}
        onStartNewCall={onStartNewCall}
      />
    );
  }

  if (error !== null) {
    return (
      <CallSummaryShell onClose={onClose} onStartNewCall={onStartNewCall}>
        <section className="wrapup-card">
          <p className="wrapup-error">{error}</p>
        </section>
      </CallSummaryShell>
    );
  }

  if (live === null) {
    return (
      <CallSummaryShell onClose={onClose} onStartNewCall={onStartNewCall}>
        <section className="wrapup-card">
          <p className="wrapup-loading">
            <span className="spinner" aria-hidden="true" />
            정리하는 중...
          </p>
        </section>
      </CallSummaryShell>
    );
  }

  return (
    <CallSummaryPanel
      call={callSummaryFromWrapUp(live)}
      onClose={onClose}
      onStartNewCall={onStartNewCall}
    />
  );
}

export function CallSummaryPanel({
  call,
  onClose,
  onStartNewCall,
}: CallSummaryPanelProps): ReactElement {
  const mode = useCallStore((state) => state.mode);
  const utterances = useCallStore((state) => state.utterances);
  const callId = useCallStore((state) => state.callId);
  const viewMode = useCallStore((state) => state.viewMode);
  const manualSearches = useCallStore((state) => state.manualSearches);
  const cards = useCallStore((state) => state.cards);
  const adoptions = useCallStore((state) => state.adoptions);
  const showLiveExtras = viewMode !== "history";

  const adopted = useMemo(
    () =>
      cards.filter((item) => adoptions[cardId(item.card)]?.adopted === true),
    [cards, adoptions],
  );
  const failed = manualSearches.filter((entry) => !entry.found);
  const resources = call.resources ?? [];

  return (
    <CallSummaryShell onClose={onClose} onStartNewCall={onStartNewCall}>
      <section className="wrapup-card">
        <div className="wrapup-card-head">
          <h3>상담 요약</h3>
        </div>
        <p className="wrapup-prose">{call.summary}</p>
        <ul className="wrapup-tags">
          {call.tags.map((tag) => (
            <li key={tag} className="wrapup-tag">
              {tag}
            </li>
          ))}
        </ul>
        {mode === "mock" && showLiveExtras ? (
          <p className="wrapup-note">
            요약·유형·후속조치는 생성 모델이 아직 없어 mock 시나리오에 미리
            적어둔 문장입니다. 발화 {utterances.length}건에서 뽑아낸 것이
            아닙니다.
          </p>
        ) : null}
      </section>

      <FollowUpChecklist title="후속 조치" items={call.followUps} />

      <section className="wrapup-card">
        <div className="wrapup-card-head">
          <h3>연계 가능한 지역자원</h3>
        </div>
        <ul className="resource-list">
          {resources.map((item) => (
            <li key={`${item.orgName}-${item.phone}`}>
              <LocalResourceCard
                orgName={item.orgName}
                address={item.address}
                phone={item.phone}
              />
            </li>
          ))}
        </ul>
      </section>

      {showLiveExtras && cards.length > 0 ? (
        <section className="wrapup-card">
          <div className="wrapup-card-head">
            <h3>카드 사용 현황</h3>
          </div>
          <div className="adopt-stats">
            <div className="adopt-stat">
              <span className="adopt-stat-num">{cards.length}</span>
              <span className="adopt-stat-label">총 카드</span>
            </div>
            <div className="adopt-stat">
              <span className="adopt-stat-num">{adopted.length}</span>
              <span className="adopt-stat-label">채택</span>
            </div>
            <div className="adopt-stat">
              <span className="adopt-stat-num">
                {cards.length - adopted.length}
              </span>
              <span className="adopt-stat-label">무시</span>
            </div>
          </div>
          {adopted.length > 0 ? (
            <ul className="adopt-titles">
              {adopted.map((item) => (
                <li key={cardId(item.card)}>{item.card.title}</li>
              ))}
            </ul>
          ) : null}
          <p className="wrapup-note">
            어떤 문서가 실제로 쓰였는지 지식베이스에 돌려주는 기록입니다.
            상담 품질을 재는 값이 아닙니다.
          </p>
        </section>
      ) : null}

      {showLiveExtras && manualSearches.length > 0 ? (
        <section className="wrapup-card">
          <div className="wrapup-card-head">
            <h3>지식베이스 공백</h3>
          </div>
          {failed.length > 0 ? (
            <>
              <p className="gap-headline">
                이번 통화에서 검색 실패 {failed.length}건 발생
              </p>
              <ul className="gap-list">
                {failed.map((entry, index) => (
                  <li key={`${entry.query}-${index}`}>{entry.query}</li>
                ))}
              </ul>
              <p className="wrapup-note">
                상담원이 직접 찾았는데 문서가 없던 질문입니다. 지식베이스
                보강 후보로 남깁니다.
              </p>
            </>
          ) : (
            <p className="gap-headline muted">
              직접 검색 {manualSearches.length}건, 모두 문서를 찾았습니다.
            </p>
          )}
        </section>
      ) : null}

      {call.sentiment !== undefined ? (
        <MoodSection sentiment={call.sentiment} isMock={mode === "mock"} />
      ) : null}

      {/* J-1 — 실시간 통화에서만 띄운다. 상담기록 조회 화면에서는 이미 지난 통화라
          전환 요청의 대상이 아니다(`_project/decisions/204`). */}
      {showLiveExtras && callId !== null ? (
        <section className="wrapup-card">
          <div className="wrapup-card-head">
            <h3>콜 라우팅 보호</h3>
          </div>
          <BlacklistRequestButton
            callId={callId}
            customerRef={customerRef(callId)}
            displayHint={displayHint(callId)}
            callDurationS={callDurationS(utterances)}
            contextExcerpt={maskedExcerpt(utterances)}
          />
        </section>
      ) : null}
    </CallSummaryShell>
  );
}

/**
 * 데모용 고객 식별자. **다산 데이터에 고객 ID 가 없다** — `_logs/2026-08-28-05-ryujun`
 * 가 F-3(반복 문의 연결)을 폐기하며 적은 것과 같은 문제다. `decisions/204` 가 정한 대로
 * **전화번호를 식별자로 가정**한다.
 *
 * ⚠ **평문 전화번호를 그대로 쓰지 않는다**(`_project/decisions/205` ③). 전화번호는
 * C-5 의 P4 이고, 자막에서 지운 값을 옆 테이블에 평문으로 두면 마스킹을 앞단에 둔
 * 의미가 사라진다. 실서버에서는 **HMAC-SHA256(번호, 서버 비밀키)**이고, 여기 mock 은
 * 그 자리를 흉내만 낸다 — **브라우저에서 해시를 만들지 않는다**(키가 클라이언트에
 * 있으면 해시가 아무것도 보호하지 못한다).
 */
function customerRef(callId: string): string {
  return `mockref_${callId.slice(-8)}`;
}

/** 화면 표시 전용. 조회·배정은 `customerRef` 로만 한다. */
function displayHint(callId: string): string {
  return `****${callId.slice(-4).padStart(4, "0")}`;
}

/** 마지막 발화의 종료 시각을 통화 길이로 본다. 실제 통화 시간은 게이트웨이가 준다. */
function callDurationS(utterances: Utterance[]): number {
  const last = utterances[utterances.length - 1];
  return last ? Math.round(last.utterance_end_ms / 1000) : 0;
}

/**
 * 관리자에게 보낼 대화 맥락.
 *
 * ⚠ **마스킹된 자막(`text`)을 쓴다. `plain_text`(원문)를 쓰지 않는다** —
 * `DASAN-MANUAL-5.5`·C-5. 원문을 실으면 마스킹을 앞단에 둔 의미가 사라진다.
 * 고객 발화만 담는다 — 판단 대상이 고객이기 때문이다.
 */
function maskedExcerpt(utterances: Utterance[]): string {
  return utterances
    .filter((u) => u.speaker === "customer")
    .slice(-6)
    .map((u) => u.text)
    .join("\n");
}

function CallSummaryShell({
  onClose,
  onStartNewCall,
  children,
}: {
  onClose: () => void;
  onStartNewCall: () => void;
  children: ReactNode;
}): ReactElement {
  return (
    <main className="wrapup call-summary">
      <div className="wrapup-topbar">
        <header className="wrapup-inner wrapup-head">
          <div>
            <p className="wrapup-eyebrow">통화 종료</p>
            <h2>통화 후 처리</h2>
          </div>
          <div className="wrapup-actions">
            <button
              type="button"
              className="compliance-dismiss wrapup-close"
              aria-label="요약 닫기"
              onClick={onClose}
            >
              <DismissIcon />
            </button>
            <button type="button" className="btn-outline" onClick={onClose}>
              돌아가기
            </button>
            <button type="button" className="btn-replay" onClick={onStartNewCall}>
              새 통화 시작
            </button>
          </div>
        </header>
      </div>
      <div className="wrapup-scroll">
        <div className="wrapup-inner">{children}</div>
      </div>
    </main>
  );
}

function moodTone(label: string): "calm" | "lift" | "peak" {
  if (label === "격앙") {
    return "peak";
  }
  if (label.includes("격앙")) {
    return "lift";
  }
  return "calm";
}

function MoodSection({
  sentiment,
  isMock,
}: {
  sentiment: SentimentSummary;
  isMock: boolean;
}): ReactElement {
  return (
    <section className="wrapup-card">
      <div className="wrapup-card-head">
        <h3>상담 분위기</h3>
        <span
          className={`mood-overall${sentiment.overall === "주의 필요" ? " is-watch" : ""}`}
        >
          {sentiment.overall}
        </span>
      </div>
      <ol className="mood-track" aria-label="통화 흐름">
        {sentiment.trajectory.map((label, index) => (
          <li key={`${label}-${index}`} className="mood-step">
            <span
              className={`mood-dot is-${moodTone(label)}`}
              aria-hidden="true"
            />
            <span className="mood-label">{label}</span>
          </li>
        ))}
      </ol>
      <p className="mood-guard">
        콜가드 경고 {sentiment.guard_flag_count}건
        {sentiment.guard_flag_count > 0
          ? " — 이번 통화에서 뜬 C-6 태그와 같은 수입니다."
          : " — 이 통화에는 콜가드 태그가 없습니다."}
      </p>
      {isMock ? (
        <p className="wrapup-note">
          감정분석 모델 연동 전 — mock 라벨입니다. 점수는 없습니다.
        </p>
      ) : null}
    </section>
  );
}

function DismissIcon(): ReactElement {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
    >
      <path d="M6 6 18 18M18 6 6 18" />
    </svg>
  );
}
