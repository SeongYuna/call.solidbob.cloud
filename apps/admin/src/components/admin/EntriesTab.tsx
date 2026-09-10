import type { ReactElement } from "react";
import type { BlacklistEntryItem, BlacklistRequestItem } from "../../types/blacklist";

/**
 * DB `blacklist_entry`엔 `display_hint`가 없다(2026-09-09 스키마 — ERD 대조로 발견).
 * 표시용 힌트는 등록이 아니라 요청(`BlacklistRequestItem.display_hint`)에만 있다 —
 * `request_id`로 원 요청을 찾아 붙인다.
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

/** J-4 블랙리스트 관리창. */
export function EntriesTab({
  entries,
  requests,
  onRelease,
}: {
  entries: BlacklistEntryItem[];
  requests: BlacklistRequestItem[];
  onRelease: (entryId: string) => void;
}): ReactElement {
  const active = entries.filter((e) => e.released_at === null);
  const released = entries.filter((e) => e.released_at !== null);

  return (
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
                  onRelease(entry.entry_id);
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
  );
}
