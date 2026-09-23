import { useEffect, useMemo, useState, type ReactElement, type ReactNode } from "react";
import type { CallWrapUp, SentimentSummary } from "../types/contract";
import {
  confirmSummary,
  fetchSummaryRevisions,
  getHistoryPlayback,
  isCoreApiConfigured,
  reviseSummary,
  type CallRecord,
  type SummaryRevisionItem,
} from "../lib/api/coreClient";
import type { CallMediatorMode } from "../lib/ws";
import { DEFAULT_LOCAL_RESOURCES } from "../mock/localResources";
import { cardId, useCallStore, type Utterance } from "../store/callStore";
import { BlackConsumerAction } from "./BlackConsumerAction";
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
  /** 상담기록 조회 전용 — `GET .../record`의 `summary_confirmed`. 이미 확정된 통화면 폼이 잠긴 채 열린다. */
  historyConfirmed?: boolean;
}

/**
 * G-2 미구현 — 서버(`closeCall`·`fetchCallRecord`)는 `local_resources`를 아직
 * 채우지 않는다. **`mode === "mock"`일 때만** mock 목록으로 대신 채운다(mock
 * WS·mock 상담기록 재생은 이미 자기 쪽에서 `DEFAULT_LOCAL_RESOURCES`를 채워
 * 들어오므로 — `mock/mockCallMediator.ts`·`mock/callHistory.ts` — 이 폴백은
 * 주로 방어적이다). 실서버 모드에서 비어 있으면 `undefined`로 그대로 둔다 —
 * "안내할 지역자원이 없다"를 mock 지역자원으로 덮지 않는다(2026-09-22).
 */
export function callSummaryFromWrapUp(
  wrapUp: CallWrapUp,
  mode: CallMediatorMode,
): CallSummaryModel {
  return {
    callId: wrapUp.call_id,
    summary: wrapUp.summary.join(" "),
    // D-2 분류가 규칙 기반이라 아직 유형이 없을 수 있다(`decisions/306`, 늘 null) —
    // 빈 문자열이면 빈 칩을 그리지 않고 태그 자체를 비운다.
    tags:
      wrapUp.tags !== undefined && wrapUp.tags.length > 0
        ? wrapUp.tags
        : wrapUp.category.length > 0
          ? [wrapUp.category]
          : [],
    followUps: wrapUp.follow_ups,
    resources:
      wrapUp.local_resources !== undefined && wrapUp.local_resources.length > 0
        ? wrapUp.local_resources
        : mode === "mock"
          ? [...DEFAULT_LOCAL_RESOURCES]
          : undefined,
    sentiment: wrapUp.sentiment,
  };
}

/**
 * `GET /hub/calls/{id}/record` → `CallWrapUp` 모양으로 바꿔서 `callSummaryFromWrapUp`을
 * 그대로 재사용한다(태그·지역자원 기본값 처리가 라이브와 같아야 한다).
 * 감정분석은 저장되지 않아 없다(모델 없음) — `sentiment`는 항상 비운다.
 */
function wrapUpFromRecord(record: CallRecord): CallWrapUp {
  return {
    call_id: record.callId,
    summary: record.summaryText !== null ? [record.summaryText] : [],
    category: record.inquiryType ?? "",
    follow_ups: record.followUpActions.map((f) => f.text),
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
  const historyRecord = useCallStore((state) => state.historyRecord);
  const mode = useCallStore((state) => state.mode);
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
    if (isCoreApiConfigured()) {
      if (historyRecord === null) {
        return (
          <CallSummaryShell onClose={onClose} onStartNewCall={onStartNewCall}>
            <section className="wrapup-card">
              <p className="wrapup-error">이 통화의 기록을 불러오지 못했습니다.</p>
            </section>
          </CallSummaryShell>
        );
      }
      if (historyRecord.summaryText === null) {
        return (
          <CallSummaryShell onClose={onClose} onStartNewCall={onStartNewCall}>
            <section className="wrapup-card">
              <p className="wrapup-error">
                이 통화는 아직 통화 후 처리가 되지 않았습니다 — 요약 초안이 없습니다.
              </p>
            </section>
          </CallSummaryShell>
        );
      }
      return (
        <CallSummaryPanel
          call={callSummaryFromWrapUp(wrapUpFromRecord(historyRecord), mode)}
          onClose={onClose}
          onStartNewCall={onStartNewCall}
          historyConfirmed={historyRecord.summaryConfirmed}
        />
      );
    }
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
        call={callSummaryFromWrapUp(playback.wrapUp, mode)}
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
      call={callSummaryFromWrapUp(live, mode)}
      onClose={onClose}
      onStartNewCall={onStartNewCall}
    />
  );
}

export function CallSummaryPanel({
  call,
  onClose,
  onStartNewCall,
  historyConfirmed,
}: CallSummaryPanelProps): ReactElement {
  const mode = useCallStore((state) => state.mode);
  const utterances = useCallStore((state) => state.utterances);
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

      {mode !== "mock" && call.callId.length > 0 ? (
        <SummaryConfirmationForm
          callId={call.callId}
          initialSummary={call.summary}
          initialInquiryType={call.tags[0] ?? ""}
          initialFollowUps={call.followUps}
          initiallyConfirmed={historyConfirmed ?? false}
        />
      ) : null}

      {showLiveExtras ? <BlackConsumerAction callId={call.callId} /> : null}

      <FollowUpChecklist title="후속 조치" items={call.followUps} />

      {/* G-2 미구현 — 실서버 모드에서 안내할 지역자원이 없으면 섹션째 렌더하지
          않는다("카드 사용 현황"·"지식베이스 공백"과 같은 패턴). mock 목록으로
          덮지 않는다(2026-09-22). */}
      {call.resources !== undefined && call.resources.length > 0 ? (
        <section className="wrapup-card">
          <div className="wrapup-card-head">
            <h3>연계 가능한 지역자원</h3>
          </div>
          <ul className="resource-list">
            {call.resources.map((item) => (
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
      ) : null}

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
      {showLiveExtras && call.callId.length > 0 ? (
        <section className="wrapup-card">
          <div className="wrapup-card-head">
            <h3>콜 라우팅 보호</h3>
          </div>
          <BlacklistRequestButton
            callId={call.callId}
            customerRef={customerRef(call.callId)}
            displayHint={displayHint(call.callId)}
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

/** 마지막 발화의 종료 시각을 통화 길이로 본다. 실제 통화 시간은 콜 미디에이터가 준다. */
function callDurationS(utterances: Utterance[]): number {
  const last = utterances[utterances.length - 1];
  return last ? Math.round(last.utterance_end_ms / 1000) : 0;
}

/**
 * 관리자에게 보낼 대화 맥락.
 *
 * ⚠ **마스킹된 자막(`text`)만 쓴다** — `DASAN-MANUAL-5.5`·C-5. 원문을 실으면
 * 마스킹을 앞단에 둔 의미가 사라진다(`Utterance`엔 원문 필드 자체가 없다,
 * `decisions/408`). 고객 발화만 담는다 — 판단 대상이 고객이기 때문이다.
 */
function maskedExcerpt(utterances: Utterance[]): string {
  return utterances
    .filter((u) => u.speaker === "customer")
    .slice(-6)
    .map((u) => u.text)
    .join("\n");
}

/**
 * `decisions/310`·`decisions/311` — 규칙 기반 초안을 상담원이 고쳐서 확정한다
 * (`POST .../summary-confirmation`), 확정 뒤에는 사유와 함께 재수정할 수 있다
 * (`POST .../summary-revision`, 확정 전이면 409). 둘 다 상담원 토큰이 필요하다.
 */
function SummaryConfirmationForm({
  callId,
  initialSummary,
  initialInquiryType,
  initialFollowUps,
  initiallyConfirmed = false,
}: {
  callId: string;
  initialSummary: string;
  initialInquiryType: string;
  initialFollowUps: readonly string[];
  /** 상담기록 조회 전용 — 이미 확정된 통화를 열면 잠긴 상태로 시작한다(정확한 확정 시각은 모른다). */
  initiallyConfirmed?: boolean;
}): ReactElement {
  const [summaryText, setSummaryText] = useState(initialSummary);
  const [inquiryType, setInquiryType] = useState(initialInquiryType);
  const [followUpsText, setFollowUpsText] = useState(initialFollowUps.join("\n"));
  const [reviseReason, setReviseReason] = useState("");
  const [confirmed, setConfirmed] = useState(initiallyConfirmed);
  const [confirmedAt, setConfirmedAt] = useState<string | null>(null);
  const [lastRevisedAt, setLastRevisedAt] = useState<string | null>(null);
  const [revising, setRevising] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function collectFollowUps(): string[] {
    return followUpsText
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
  }

  async function handleConfirm(): Promise<void> {
    if (summaryText.trim().length === 0) {
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const result = await confirmSummary(callId, {
        summaryText: summaryText.trim(),
        inquiryType: inquiryType.trim().length > 0 ? inquiryType.trim() : null,
        followUpActions: collectFollowUps(),
      });
      setConfirmed(true);
      setConfirmedAt(result.confirmedAt);
    } catch (err) {
      setError(err instanceof Error ? err.message : "요약 확정에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRevise(): Promise<void> {
    if (summaryText.trim().length === 0 || reviseReason.trim().length === 0) {
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const result = await reviseSummary(callId, {
        summaryText: summaryText.trim(),
        reason: reviseReason.trim(),
        inquiryType: inquiryType.trim().length > 0 ? inquiryType.trim() : null,
        followUpActions: collectFollowUps(),
      });
      setLastRevisedAt(result.revisedAt);
      setReviseReason("");
      setRevising(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "요약 재수정에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  }

  const locked = confirmed && !revising;

  if (locked) {
    return (
      <>
        <section className="wrapup-card">
          <div className="wrapup-card-head">
            <h3>요약 확정</h3>
          </div>
          <p className="wrapup-note">
            {confirmedAt !== null
              ? `${new Date(confirmedAt).toLocaleString("ko-KR")}에 확정했습니다.`
              : "이미 확정된 요약입니다."}
            {lastRevisedAt !== null
              ? ` 최근 재수정: ${new Date(lastRevisedAt).toLocaleString("ko-KR")}.`
              : ""}
          </p>
          {error !== null ? (
            <p className="wrapup-error" role="alert">
              {error}
            </p>
          ) : null}
          <button
            type="button"
            className="btn-outline"
            onClick={() => {
              setError(null);
              setRevising(true);
            }}
          >
            재수정
          </button>
        </section>
        <SummaryRevisionHistory callId={callId} refreshKey={lastRevisedAt} />
      </>
    );
  }

  const isRevision = confirmed;

  return (
    <>
      <section className="wrapup-card">
      <div className="wrapup-card-head">
        <h3>{isRevision ? "요약 재수정" : "요약 확정"}</h3>
      </div>
      <p className="wrapup-note">
        {isRevision
          ? "확정된 요약을 고칩니다 — 사유가 필수이고, 고치기 전 값은 이력으로 남습니다."
          : "위 요약은 규칙 기반 초안입니다. 고친 뒤 확정하면 상담기록에 저장됩니다 — 확정은 한 번뿐이고, 이 통화로 다시 초안을 만들 수 없습니다."}
      </p>
      {error !== null ? (
        <p className="wrapup-error" role="alert">
          {error}
        </p>
      ) : null}
      <label className="admin-settings-field">
        <span>요약</span>
        <textarea
          value={summaryText}
          rows={4}
          onChange={(event) => {
            setSummaryText(event.target.value);
          }}
        />
      </label>
      <label className="admin-settings-field">
        <span>문의 유형 (선택)</span>
        <input
          type="text"
          value={inquiryType}
          onChange={(event) => {
            setInquiryType(event.target.value);
          }}
        />
      </label>
      <label className="admin-settings-field">
        <span>후속조치 (한 줄에 하나씩)</span>
        <textarea
          value={followUpsText}
          rows={3}
          onChange={(event) => {
            setFollowUpsText(event.target.value);
          }}
        />
      </label>
      {isRevision ? (
        <label className="admin-settings-field">
          <span>재수정 사유 (필수)</span>
          <textarea
            value={reviseReason}
            rows={2}
            onChange={(event) => {
              setReviseReason(event.target.value);
            }}
          />
        </label>
      ) : null}
      <div style={{ display: "flex", gap: 8 }}>
        <button
          type="button"
          className="btn-outline"
          disabled={
            saving ||
            summaryText.trim().length === 0 ||
            (isRevision && reviseReason.trim().length === 0)
          }
          onClick={() => {
            void (isRevision ? handleRevise() : handleConfirm());
          }}
        >
          {saving ? "저장 중..." : isRevision ? "재수정 확정" : "요약 확정"}
        </button>
        {isRevision ? (
          <button
            type="button"
            className="btn-outline"
            disabled={saving}
            onClick={() => {
              setRevising(false);
              setError(null);
              setReviseReason("");
            }}
          >
            취소
          </button>
        ) : null}
      </div>
      </section>
      {isRevision ? <SummaryRevisionHistory callId={callId} refreshKey={lastRevisedAt} /> : null}
    </>
  );
}

/**
 * `GET .../summary-revisions` — 확정된 요약을 고친 이력, 오래된 순.
 *
 * `lastRevisedAt`(위 잠금 카드의 "최근 재수정: ..." 문구)과 겹치지만 대체하지
 * 않는다 — 그 문구는 재수정 직후 서버를 다시 부르지 않고도 바로 채워지는
 * 가벼운 요약이고, 이 목록은 그 아래서 필요할 때만 펼쳐 보는 상세(이전
 * 요약·이전 유형·사유)다. "카드 사용 현황"이 총계와 채택 목록을 같이 두는
 * 것과 같은 방식 — 하나가 실패해도(fetch 오류) 다른 하나는 여전히 보인다.
 *
 * `refreshKey`에 `lastRevisedAt`을 그대로 받는다 — 재수정이 성공할 때마다
 * 값이 바뀌어 새로 부른다. 첫 마운트(값이 `null`)에도 한 번 부른다.
 */
function SummaryRevisionHistory({
  callId,
  refreshKey,
}: {
  callId: string;
  refreshKey: string | null;
}): ReactElement {
  const [state, setState] = useState<
    | { status: "loading" }
    | { status: "ready"; revisions: SummaryRevisionItem[] }
    | { status: "error"; message: string }
  >({ status: "loading" });

  useEffect(() => {
    let alive = true;
    setState({ status: "loading" });
    fetchSummaryRevisions(callId)
      .then((revisions) => {
        if (alive) {
          setState({ status: "ready", revisions });
        }
      })
      .catch((error: unknown) => {
        if (alive) {
          setState({
            status: "error",
            message: error instanceof Error ? error.message : "재수정 이력을 불러오지 못했습니다.",
          });
        }
      });
    return () => {
      alive = false;
    };
  }, [callId, refreshKey]);

  return (
    <section className="wrapup-card">
      <div className="wrapup-card-head">
        <h3>재수정 이력</h3>
      </div>
      {state.status === "loading" ? (
        <p className="wrapup-loading">
          <span className="spinner" aria-hidden="true" />
          불러오는 중...
        </p>
      ) : state.status === "error" ? (
        <p className="wrapup-error" role="alert">
          {state.message}
        </p>
      ) : state.revisions.length === 0 ? (
        <p className="wrapup-note">재수정한 적이 없습니다.</p>
      ) : (
        <ul className="adopt-titles">
          {state.revisions.map((rev) => (
            <li key={rev.revisionId}>
              <span>
                <strong>{new Date(rev.revisedAt).toLocaleString("ko-KR")}</strong> · 사유:{" "}
                {rev.reason}
                <br />
                이전 요약: {rev.previousSummaryText}
                {rev.previousInquiryType !== null
                  ? ` · 이전 유형: ${rev.previousInquiryType}`
                  : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
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
  const viewMode = useCallStore((state) => state.viewMode);
  const setHistoryView = useCallStore((state) => state.setHistoryView);
  const isHistory = viewMode === "history";
  return (
    <main className="wrapup call-summary">
      <div className="wrapup-topbar">
        <header className="wrapup-inner wrapup-head">
          <div>
            <p className="wrapup-eyebrow">{isHistory ? "상담기록" : "통화 종료"}</p>
            <h2>{isHistory ? "지난 통화 요약" : "통화 후 처리"}</h2>
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
            {isHistory ? (
              <button
                type="button"
                className="btn-outline"
                onClick={() => {
                  setHistoryView("transcript");
                }}
              >
                자막 보기
              </button>
            ) : null}
            <button type="button" className="btn-outline" onClick={onClose}>
              돌아가기
            </button>
            {isHistory ? null : (
              <button type="button" className="btn-replay" onClick={onStartNewCall}>
                새 통화 시작
              </button>
            )}
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
