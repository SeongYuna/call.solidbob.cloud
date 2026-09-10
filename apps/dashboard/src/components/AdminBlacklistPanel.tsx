import { useState, type ReactElement } from "react";
import { abuseTotal, hasDistress } from "../lib/blacklist/collectEvidence";
import { getMockAgentAccount } from "../mock/agentAuth";
import { useCallStore } from "../store/callStore";
import type { BlacklistEntryItem, BlacklistRequestItem } from "../types/contract";

/**
 * DB `blacklist_entry`엔 `display_hint`가 없다(ERD 대조로 발견, 2026-09-10) —
 * 요청(`blacklist_request`)에만 있어 `request_id`로 찾아 붙인다.
 */
function entryDisplayHint(
  entry: BlacklistEntryItem,
  requests: BlacklistRequestItem[],
): string {
  return (
    requests.find((r) => r.request_id === entry.request_id)?.display_hint ??
    "****"
  );
}

type Tab = "requests" | "entries";

/**
 * J-3 — 관리자 대시보드. **승인요청창**과 **블랙리스트 관리창** 둘을 한 화면에서 오간다.
 *
 * `_project/decisions/204`. 관리자가 **통화를 다시 듣지 않고** 판단할 수 있어야 하므로
 * 요청 카드에 근거를 전부 펼쳐 둔다 — 통화 시간·폭언 건수·통화 온도 이상 구간,
 * 그리고 **마스킹된 대화 맥락**.
 *
 * ⚠ 근거는 전부 **셀 수 있는 건수**다. 위험도 점수를 만들지 않는다(부록 A-1).
 */
export function AdminBlacklistPanel({
  onExit,
}: {
  onExit: () => void;
}): ReactElement {
  const requests = useCallStore((s) => s.blacklistRequests);
  const entries = useCallStore((s) => s.blacklistEntries);
  const decide = useCallStore((s) => s.decideBlacklistRequest);
  const release = useCallStore((s) => s.releaseBlacklistEntry);
  const [tab, setTab] = useState<Tab>("requests");

  const pending = requests.filter((r) => r.status === "pending");
  const decided = requests.filter((r) => r.status !== "pending");
  const active = entries.filter((e) => e.released_at === null);
  const released = entries.filter((e) => e.released_at !== null);
  const admin = getMockAgentAccount().name;

  return (
    <main className="wrapup admin-panel">
      <div className="wrapup-topbar">
        <header className="wrapup-inner wrapup-head">
          <div>
            <p className="wrapup-eyebrow">관리자</p>
            <h2>블랙리스트 관리</h2>
          </div>
          <div className="wrapup-actions">
            <button type="button" className="btn-outline" onClick={onExit}>
              상담 화면으로
            </button>
          </div>
        </header>
        <nav className="admin-tabs" aria-label="관리자 화면 전환">
          <button
            type="button"
            className={tab === "requests" ? "admin-tab is-active" : "admin-tab"}
            onClick={() => {
              setTab("requests");
            }}
          >
            승인요청 <span className="admin-count">{pending.length}</span>
          </button>
          <button
            type="button"
            className={tab === "entries" ? "admin-tab is-active" : "admin-tab"}
            onClick={() => {
              setTab("entries");
            }}
          >
            블랙리스트 <span className="admin-count">{active.length}</span>
          </button>
        </nav>
      </div>

      <div className="wrapup-scroll">
        <div className="wrapup-inner">
          {tab === "requests" ? (
            <section aria-label="승인요청">
              {pending.length === 0 ? (
                <p className="admin-empty">대기 중인 요청이 없습니다.</p>
              ) : (
                pending.map((request) => (
                  <RequestCard
                    key={request.request_id}
                    request={request}
                    onApprove={() => {
                      decide(request.request_id, true, admin);
                    }}
                    onReject={() => {
                      decide(request.request_id, false, admin);
                    }}
                  />
                ))
              )}

              {decided.length > 0 ? (
                <>
                  <h3 className="admin-section">처리된 요청</h3>
                  <ul className="admin-list">
                    {decided.map((r) => (
                      <li key={r.request_id}>
                        <span className="admin-ref">{r.display_hint}</span>
                        <span
                          className={
                            r.status === "approved"
                              ? "admin-badge is-approved"
                              : "admin-badge"
                          }
                        >
                          {r.status === "approved" ? "승인" : "반려"}
                        </span>
                        <span className="admin-meta">{r.decided_by}</span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
            </section>
          ) : (
            <section aria-label="블랙리스트">
              <p className="admin-help">
                등록된 고객의 전화도 <strong>정상적으로 받습니다.</strong> 바뀌는 것은
                근속 3년 이상 상담사에게 배정된다는 점 하나입니다.
              </p>
              {active.length === 0 ? (
                <p className="admin-empty">등록된 고객이 없습니다.</p>
              ) : (
                <ul className="admin-list">
                  {active.map((entry) => (
                    <li key={entry.entry_id}>
                      {/* ⚠ 전체 식별자(HMAC)를 화면에 내지 않는다 — 표시는 힌트만
                          (`_project/decisions/205` ③). */}
                      <span className="admin-ref">
                        {entryDisplayHint(entry, requests)}
                      </span>
                      <span className="admin-meta">
                        {new Date(entry.expires_at).toLocaleDateString("ko-KR")} 만료
                      </span>
                      <button
                        type="button"
                        className="btn-outline admin-release"
                        onClick={() => {
                          release(entry.entry_id, admin, "관리자 해제");
                        }}
                      >
                        해제
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              {released.length > 0 ? (
                <>
                  {/* 해제 기록을 지우지 않는다 — 지우면 「왜 풀렸는지」가 사라진다
                      (절대 원칙 8). DB 스키마도 같은 방식이다. */}
                  <h3 className="admin-section">해제된 기록</h3>
                  <ul className="admin-list is-muted">
                    {released.map((entry) => (
                      <li key={entry.entry_id}>
                        <span className="admin-ref">
                          {entryDisplayHint(entry, requests)}
                        </span>
                        <span className="admin-meta">
                          {entry.released_by} · {entry.release_reason ?? "사유 없음"}
                        </span>
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
            </section>
          )}
        </div>
      </div>
    </main>
  );
}

function RequestCard({
  request,
  onApprove,
  onReject,
}: {
  request: BlacklistRequestItem;
  onApprove: () => void;
  onReject: () => void;
}): ReactElement {
  const abuse = abuseTotal(request.evidence);
  const distress = hasDistress(request.evidence);
  const minutes = Math.round(request.evidence.call_duration_s / 60);

  return (
    <article className="wrapup-card admin-request">
      <header className="admin-request-head">
        <span className="admin-ref">{request.display_hint}</span>
        <span className="admin-meta">
          {request.requested_by} · 통화 {minutes}분
        </span>
      </header>

      {distress ? (
        <p className="blacklist-distress" role="alert">
          ⚠ 이 통화에 <strong>위기 신호</strong> {request.evidence.distress_count}건이
          있습니다. 폭언과 다른 상황일 수 있어 <strong>전환 근거에서 제외</strong>했습니다 —
          전문 상담 기관 연결을 먼저 검토해 주세요.
        </p>
      ) : null}

      <dl className="blacklist-evidence">
        <div>
          <dt>폭언·위협</dt>
          <dd>{abuse}건</dd>
        </div>
        <div>
          <dt>통화 온도 이상 구간</dt>
          <dd>{request.evidence.temperature_outliers}건</dd>
        </div>
        <div>
          <dt>통화 시간</dt>
          <dd>{minutes}분</dd>
        </div>
      </dl>

      <h4 className="admin-subhead">상담원 사유</h4>
      <p className="admin-reason">{request.reason}</p>

      <h4 className="admin-subhead">대화 맥락</h4>
      {/* ⚠ 마스킹된 자막이다. 원문이 아니다 — DASAN-MANUAL-5.5 · C-5. */}
      <p className="admin-excerpt">{request.context_excerpt}</p>

      <div className="blacklist-actions">
        <button type="button" className="btn-outline" onClick={onReject}>
          반려
        </button>
        <button type="button" className="btn-replay" onClick={onApprove}>
          승인
        </button>
      </div>
    </article>
  );
}
