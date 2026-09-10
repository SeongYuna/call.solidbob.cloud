import { useMemo, useState, type ReactElement } from "react";
import { QA_REVIEW_FIXTURES, type QaReviewFixture } from "../../mock/qaReviewFixtures";

/**
 * QA 리뷰 큐. Zendesk QA·MaestroQA류 도구의 "리뷰 대상 통화 큐"를 본떴다 —
 * 콜가드 태그가 뜬 통화·감정분석이 "주의 필요"로 본 통화를 모아 보여준다.
 * 새로 만드는 판정이 아니라 이미 있는 값을 필터링만 한다.
 *
 * ⚠ 2026-09-10 — 앱 분리로 `apps/dashboard`의 상담기록 mock을 더는 못 쓴다.
 * 지금은 `mock/qaReviewFixtures.ts`의 예시 몇 건으로 화면만 먼저 만들고,
 * 백엔드가 붙으면 통화 목록 조회 API로 바꾼다.
 */
export function QaReviewTab(): ReactElement {
  const rows = useMemo<QaReviewFixture[]>(
    () =>
      QA_REVIEW_FIXTURES.filter(
        (row) => row.overall === "주의 필요" || row.guardFlagCount > 0,
      ),
    [],
  );

  const [openCallId, setOpenCallId] = useState<string | null>(null);
  const opened = rows.find((row) => row.call_id === openCallId) ?? null;

  if (rows.length === 0) {
    return (
      <section aria-label="QA 리뷰 큐">
        <p className="admin-empty">리뷰가 필요한 통화가 없습니다.</p>
      </section>
    );
  }

  return (
    <section aria-label="QA 리뷰 큐">
      <p className="admin-help">
        상담 분위기가 "주의 필요"였거나 콜가드 경고가 뜬 통화입니다. 상담원
        평가가 아니라 <strong>다시 들어볼 통화를 고르는 목록</strong>입니다.
      </p>
      <ul className="admin-list">
        {rows.map((row) => (
          <li key={row.call_id}>
            <span className="admin-ref">{row.inquiry_type}</span>
            <span className="admin-meta">
              {row.overall === "주의 필요" ? "상담 분위기 주의 필요" : null}
              {row.overall === "주의 필요" && row.guardFlagCount > 0 ? " · " : null}
              {row.guardFlagCount > 0 ? `콜가드 경고 ${row.guardFlagCount}건` : null}
            </span>
            <button
              type="button"
              className="btn-outline admin-release"
              onClick={() => {
                setOpenCallId(row.call_id === openCallId ? null : row.call_id);
              }}
            >
              {row.call_id === openCallId ? "닫기" : "리뷰"}
            </button>
          </li>
        ))}
      </ul>

      {opened !== null ? (
        <article className="wrapup-card admin-request">
          <div className="admin-request-head">
            <h4 className="admin-subhead">{opened.inquiry_type}</h4>
          </div>
          <p className="admin-reason">{opened.summary}</p>
          <ol className="mood-track" aria-label="통화 흐름">
            {opened.trajectory.map((label, index) => (
              <li key={`${label}-${index}`} className="mood-step">
                <span className="mood-label">{label}</span>
              </li>
            ))}
          </ol>
        </article>
      ) : null}
    </section>
  );
}
