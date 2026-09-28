import { useEffect, useMemo, useState, type ReactElement } from "react";
import { useAuthStore } from "../../lib/auth/authStore";
import {
  fetchRecentBlacklistExpiryChanges,
  type ExpiryChangeItem,
} from "../../lib/api/hubClient";
import type { BlacklistEntryItem, BlacklistRequestItem } from "../../types/blacklist";

interface AuditEntry {
  at: string;
  actor: string;
  action: "승인" | "반려" | "해제" | "재설정";
  detail: string;
}

type ExpiryChangeState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; changes: ExpiryChangeItem[] }
  | { status: "error" };

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleDateString("ko-KR");
}

/**
 * 승인·반려·해제·만료일 재설정을 한 줄로 합쳐 최근 순으로 정렬한다.
 * 재설정은 `GET /hub/blacklist-expiry-changes`(QA Q-67)가 준다 — 사유는 서버가 마스킹해 온 값이다.
 */
export function buildAuditRows(
  requests: BlacklistRequestItem[],
  entries: BlacklistEntryItem[],
  expiryChanges: ExpiryChangeItem[],
): AuditEntry[] {
  const list: AuditEntry[] = [];
  for (const r of requests) {
    if (r.status === "pending" || r.decided_at === null) {
      continue;
    }
    list.push({
      at: r.decided_at,
      actor: r.decided_by ?? "알 수 없음",
      action: r.status === "approved" ? "승인" : "반려",
      detail: r.display_hint ?? "****",
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
  for (const c of expiryChanges) {
    if (c.changed_at === "") {
      continue;
    }
    list.push({
      at: c.changed_at,
      actor: c.changed_by || "알 수 없음",
      action: "재설정",
      detail: `만료 ${formatDate(c.previous_expires_at)} → ${formatDate(c.new_expires_at)} · ${c.reason || "사유 없음"}`,
    });
  }
  // 세 출처의 시각 표기(시간대 접미사)가 다를 수 있어 문자열이 아니라 시각으로 비교한다.
  return list.sort((a, b) => timeOf(b.at) - timeOf(a.at));
}

function timeOf(iso: string): number {
  const t = new Date(iso).getTime();
  return Number.isNaN(t) ? 0 : t;
}

/**
 * 감사 로그. 대부분의 admin 패널이 갖는 "누가 언제 뭘 승인·해제했는지" 로그를
 * 본떴다 — 새 데이터를 쌓지 않는다. `blacklist_request.decided_by`/`decided_at`,
 * `blacklist_entry.released_by`/`release_reason`은 이미 있는 값이라 여기서는
 * 시간순으로 합쳐 보여주기만 한다.
 *
 * 2026-09-28 — 만료일 변경(연장·단축)도 관리자 행위인데 빠져 있었다(QA Q-67).
 * 서버의 최근 변경 목록(`GET /hub/blacklist-expiry-changes?limit=50`)을 같이 읽어
 * 「재설정」 줄로 합친다. 불러오지 못하면 조용히 빼지 않고 그 사실을 한 줄로 알린다.
 */
export function AuditLogTab({
  requests,
  entries,
}: {
  requests: BlacklistRequestItem[];
  entries: BlacklistEntryItem[];
}): ReactElement {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [expiry, setExpiry] = useState<ExpiryChangeState>({ status: "idle" });

  useEffect(() => {
    if (accessToken === null) {
      setExpiry({ status: "idle" });
      return;
    }
    let cancelled = false;
    setExpiry({ status: "loading" });
    fetchRecentBlacklistExpiryChanges(accessToken, 50)
      .then((changes) => {
        if (!cancelled) {
          setExpiry({ status: "ready", changes });
        }
      })
      .catch(() => {
        if (!cancelled) {
          setExpiry({ status: "error" });
        }
      });
    return () => {
      cancelled = true;
    };
    // 등록 목록이 바뀌면(연장·해제 직후) 다시 읽는다.
  }, [accessToken, entries]);

  const rows = useMemo<AuditEntry[]>(
    () =>
      buildAuditRows(
        requests,
        entries,
        expiry.status === "ready" ? expiry.changes : [],
      ),
    [requests, entries, expiry],
  );

  const expiryNote =
    expiry.status === "error" ? (
      <p className="admin-help" role="status">
        만료일 재설정 이력을 불러오지 못했습니다 — 아래 목록에 재설정은 빠져 있습니다.
      </p>
    ) : expiry.status === "idle" ? (
      <p className="admin-help">로그인하면 만료일 재설정 이력도 함께 보입니다.</p>
    ) : null;

  if (rows.length === 0) {
    return (
      <section aria-label="감사 로그">
        {expiryNote}
        <p className="admin-empty">
          {expiry.status === "loading"
            ? "감사 로그를 불러오는 중..."
            : "아직 승인·반려·해제·재설정 이력이 없습니다."}
        </p>
      </section>
    );
  }

  return (
    <section aria-label="감사 로그">
      {expiryNote}
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
