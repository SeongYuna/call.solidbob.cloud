import { useMemo, type ReactElement } from "react";
import type { BlacklistEntryItem, BlacklistRequestItem } from "../../types/blacklist";

interface AuditEntry {
  at: string;
  actor: string;
  action: "승인" | "반려" | "해제";
  detail: string;
}

/**
 * 감사 로그. 대부분의 admin 패널이 갖는 "누가 언제 뭘 승인·해제했는지" 로그를
 * 본떴다 — 새 데이터를 쌓지 않는다. `blacklist_request.decided_by`/`decided_at`,
 * `blacklist_entry.released_by`/`release_reason`은 이미 있는 값이라 여기서는
 * 시간순으로 합쳐 보여주기만 한다.
 */
export function AuditLogTab({
  requests,
  entries,
}: {
  requests: BlacklistRequestItem[];
  entries: BlacklistEntryItem[];
}): ReactElement {
  const rows = useMemo<AuditEntry[]>(() => {
    const list: AuditEntry[] = [];
    for (const r of requests) {
      if (r.status === "pending" || r.decided_at === null) {
        continue;
      }
      list.push({
        at: r.decided_at,
        actor: r.decided_by ?? "알 수 없음",
        action: r.status === "approved" ? "승인" : "반려",
        detail: r.display_hint,
      });
    }
    for (const e of entries) {
      if (e.released_at === null) {
        continue;
      }
      list.push({
        at: e.released_at,
        actor: e.released_by ?? "알 수 없음",
        action: "해제",
        detail: e.release_reason ?? "사유 없음",
      });
    }
    return list.sort((a, b) => (a.at < b.at ? 1 : -1));
  }, [requests, entries]);

  if (rows.length === 0) {
    return (
      <section aria-label="감사 로그">
        <p className="admin-empty">아직 승인·반려·해제 이력이 없습니다.</p>
      </section>
    );
  }

  return (
    <section aria-label="감사 로그">
      <ul className="admin-list">
        {rows.map((row, index) => (
          <li key={`${row.at}-${index}`}>
            <span
              className={
                row.action === "승인"
                  ? "admin-badge is-approved"
                  : "admin-badge"
              }
            >
              {row.action}
            </span>
            <span className="admin-meta">
              {row.detail} · {row.actor} ·{" "}
              {new Date(row.at).toLocaleString("ko-KR")}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
