import { useState, type ReactElement } from "react";
import { abuseTotal, hasDistress } from "../../lib/blacklist/collectEvidence";
import type { BlacklistRequestItem } from "../../types/blacklist";

/**
 * J-3 승인요청창. 관리자가 **통화를 다시 듣지 않고** 판단할 수 있어야 하므로
 * 요청 카드에 근거를 전부 펼쳐 둔다 — 통화 시간·폭언 건수·통화 온도 이상 구간,
 * 그리고 **마스킹된 대화 맥락**.
 *
 * ⚠ 근거는 전부 **셀 수 있는 건수**다. 위험도 점수를 만들지 않는다(부록 A-1).
 */
export function RequestsTab({
  requests,
  defaultExpiryMonths,
  onApprove,
  onReject,
}: {
  requests: BlacklistRequestItem[];
  /** 설정 탭의 기본값 — 승인 카드에 미리 채워지지만 건마다 바꿀 수 있다. */
  defaultExpiryMonths: number;
  onApprove: (requestId: string, expiryMonths: number) => void;
  onReject: (requestId: string) => void;
}): ReactElement {
  const pending = requests.filter((r) => r.status === "pending");
  const decided = requests.filter((r) => r.status !== "pending");

  return (
    <section aria-label="승인요청">
      {pending.length === 0 ? (
        <p className="admin-empty">대기 중인 요청이 없습니다.</p>
      ) : (
        pending.map((request) => (
          <RequestCard
            key={request.request_id}
            request={request}
            defaultExpiryMonths={defaultExpiryMonths}
            onApprove={(months) => {
              onApprove(request.request_id, months);
            }}
            onReject={() => {
              onReject(request.request_id);
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
  );
}

function RequestCard({
  request,
  defaultExpiryMonths,
  onApprove,
  onReject,
}: {
  request: BlacklistRequestItem;
  defaultExpiryMonths: number;
  onApprove: (expiryMonths: number) => void;
  onReject: () => void;
}): ReactElement {
  const abuse = abuseTotal(request.evidence);
  const distress = hasDistress(request.evidence);
  const minutes = Math.round(request.evidence.call_duration_s / 60);
  // 건마다 심각도가 다르다 — 기본값으로 미리 채우되 승인 전에 바꿀 수 있다
  // (2026-09-10, "고객 각각으로는 안 되나" 피드백).
  const [expiryMonths, setExpiryMonths] = useState(defaultExpiryMonths);

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

      <label className="admin-inline-field">
        <span>승인 시 등록 기간 (개월)</span>
        <input
          type="number"
          min={1}
          max={24}
          value={expiryMonths}
          onChange={(event) => {
            const next = Number(event.target.value);
            if (Number.isFinite(next) && next >= 1) {
              setExpiryMonths(next);
            }
          }}
        />
      </label>

      <div className="blacklist-actions">
        <button type="button" className="btn-outline" onClick={onReject}>
          반려
        </button>
        <button
          type="button"
          className="btn-replay"
          onClick={() => {
            onApprove(expiryMonths);
          }}
        >
          승인
        </button>
      </div>
    </article>
  );
}
