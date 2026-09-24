import { useState, type ReactElement } from "react";
import { useAuthStore } from "../../lib/auth/authStore";
import { fetchBlacklistExpiryChanges, type ExpiryChangeItem } from "../../lib/api/hubClient";
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

/** `adminStore.extendEntry`가 서버에 보내는 것과 같은 계산(`Math.round(months * 30)`일, 지금부터). */
function previewExpiryDate(months: number): string {
  const days = Math.round(months * 30);
  const date = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  return date.toLocaleDateString("ko-KR");
}

type EntryFilter = "all" | "new" | "repeat";

/**
 * "기존(재범)" 판정 — 같은 customer_ref로 지금 이 행 말고 다른 등록 이력(해제된 것
 * 포함)이 하나라도 있으면 재범이다. 「고객 1명 = 1행」이 아니라 「등록 1건 = 1행」
 * 구조라서(`decisions/205` ②) customer_ref로 묶어야 재등록 여부를 알 수 있다.
 */
function isRepeatOffender(
  entry: BlacklistEntryItem,
  allEntries: BlacklistEntryItem[],
): boolean {
  return allEntries.some(
    (e) => e.entry_id !== entry.entry_id && e.customer_ref === entry.customer_ref,
  );
}

/** Requirement: J-3 블랙리스트 관리창. */
export function EntriesTab({
  entries,
  requests,
  defaultExpiryMonths,
  onRelease,
  onExtend,
}: {
  entries: BlacklistEntryItem[];
  requests: BlacklistRequestItem[];
  defaultExpiryMonths: number;
  onRelease: (entryId: string, reason: string) => void;
  onExtend: (entryId: string, months: number, reason: string) => void;
}): ReactElement {
  const [filter, setFilter] = useState<EntryFilter>("all");
  const active = entries.filter((e) => e.released_at === null);
  const released = entries.filter((e) => e.released_at !== null);

  const newCount = active.filter((e) => !isRepeatOffender(e, entries)).length;
  const repeatCount = active.length - newCount;
  const filtered = active.filter((e) => {
    if (filter === "all") {
      return true;
    }
    const repeat = isRepeatOffender(e, entries);
    return filter === "repeat" ? repeat : !repeat;
  });

  return (
    <section aria-label="블랙리스트">
      {/* ⚠ "이후 통화부터 근속 3년 이상 상담사 우선 배정 판정이 기록에 남습니다"를 뺐다 —
          콜 미디에이터 배선을 2026-09-22에 만들었다가 같은 날 되돌렸다(검토 전 롤백).
          판정 호출이 다시 없으니 이 문장은 다시 거짓이다. `decisions/407` ·
          `w7-j5-routing-caller` 참고. 배선이 다시 켜지면 채운다. */}
      <p className="admin-help">
        등록된 고객의 전화도 <strong>정상적으로 받습니다</strong> — 차단이 아닙니다.
      </p>
      <div className="admin-tabs admin-subfilter" role="tablist" aria-label="신규·기존 분류">
        <FilterChip label="전체" count={active.length} active={filter === "all"} onClick={() => setFilter("all")} />
        <FilterChip label="신규" count={newCount} active={filter === "new"} onClick={() => setFilter("new")} />
        <FilterChip label="기존(재범)" count={repeatCount} active={filter === "repeat"} onClick={() => setFilter("repeat")} />
      </div>
      {active.length === 0 ? (
        <p className="admin-empty">등록된 고객이 없습니다.</p>
      ) : filtered.length === 0 ? (
        <p className="admin-empty">
          {filter === "new" ? "신규 등록된 고객이 없습니다." : "기존(재범) 등록된 고객이 없습니다."}
        </p>
      ) : (
        <ul className="admin-list">
          {filtered.map((entry) => (
            <EntryRow
              key={entry.entry_id}
              entry={entry}
              displayHint={entryDisplayHint(entry, requests)}
              isRepeat={isRepeatOffender(entry, entries)}
              defaultExpiryMonths={defaultExpiryMonths}
              onRelease={(reason) => {
                onRelease(entry.entry_id, reason);
              }}
              onExtend={(months, reason) => {
                onExtend(entry.entry_id, months, reason);
              }}
            />
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

function FilterChip({
  label,
  count,
  active,
  onClick,
}: {
  label: string;
  count: number;
  active: boolean;
  onClick: () => void;
}): ReactElement {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={`admin-tab${active ? " is-active" : ""}`}
      onClick={onClick}
    >
      {label}
      <span className="admin-count">{count}</span>
    </button>
  );
}

function EntryRow({
  entry,
  displayHint,
  isRepeat,
  defaultExpiryMonths,
  onRelease,
  onExtend,
}: {
  entry: BlacklistEntryItem;
  displayHint: string;
  isRepeat: boolean;
  defaultExpiryMonths: number;
  onRelease: (reason: string) => void;
  onExtend: (months: number, reason: string) => void;
}): ReactElement {
  // 등록 하나하나 심각도가 다르다 — 연장·단축 기간을 건마다 따로 잡는다
  // (2026-09-10, "고객 각각으로는 안 되나" 피드백).
  const [months, setMonths] = useState(defaultExpiryMonths);
  // `decisions/309` — 연장·단축·해제 모두 사유가 서버 필수값이다. 버튼을
  // 하드코딩 문자열("관리자 해제")로 채우는 대신 실제 입력을 받는다.
  const [reason, setReason] = useState("");
  const reasonFilled = reason.trim().length > 0;

  const accessToken = useAuthStore((s) => s.accessToken);
  const [history, setHistory] = useState<
    | { status: "collapsed" }
    | { status: "loading" }
    | { status: "ready"; changes: ExpiryChangeItem[] }
    | { status: "error"; message: string }
  >({ status: "collapsed" });

  async function loadHistory(): Promise<void> {
    if (accessToken === null) {
      setHistory({ status: "error", message: "로그인이 필요합니다." });
      return;
    }
    setHistory({ status: "loading" });
    try {
      const changes = await fetchBlacklistExpiryChanges(accessToken, entry.entry_id);
      setHistory({ status: "ready", changes });
    } catch (error) {
      setHistory({
        status: "error",
        message: error instanceof Error ? error.message : "변경 이력을 불러오지 못했습니다.",
      });
    }
  }

  function toggleHistory(): void {
    if (history.status === "collapsed" || history.status === "error") {
      void loadHistory();
      return;
    }
    setHistory({ status: "collapsed" });
  }

  return (
    <li className="admin-entry-row">
      <div className="admin-entry-row-main">
        {/* ⚠ 전체 식별자(HMAC)를 화면에 내지 않는다 — 표시는 힌트만
            (`_project/decisions/205` ③). */}
        <span className="admin-ref">{displayHint}</span>
        <span className={`admin-repeat-badge${isRepeat ? " is-repeat" : ""}`}>
          {isRepeat ? "기존(재범)" : "신규"}
        </span>
        <span className="admin-meta">
          {new Date(entry.approved_at).toLocaleDateString("ko-KR")} 등록
        </span>
        <span className="admin-meta">
          {new Date(entry.expires_at).toLocaleDateString("ko-KR")} 만료
        </span>
        <button
          type="button"
          className="btn-outline"
          aria-expanded={history.status === "loading" || history.status === "ready"}
          onClick={toggleHistory}
        >
          {history.status === "loading" || history.status === "ready"
            ? "변경 이력 숨기기"
            : "변경 이력 보기"}
        </button>
      </div>
      <div className="admin-entry-row-actions">
        <input
          type="text"
          className="admin-entry-reason-input"
          aria-label="연장·단축·해제 사유"
          placeholder="사유 입력(필수)"
          value={reason}
          onChange={(event) => {
            setReason(event.target.value);
          }}
        />
        <input
          type="number"
          min={1}
          max={12}
          className="admin-entry-extend-input"
          aria-label="연장·단축할 기간 (개월)"
          value={months}
          onChange={(event) => {
            const next = Number(event.target.value);
            if (Number.isFinite(next) && next >= 1) {
              setMonths(next);
            }
          }}
        />
        {/* "재설정"은 기존 만료일에 더하는 게 아니라 **지금부터** 다시 잡는다 — 입력칸이
            기본값(전역 설정)으로 채워져 있어, 손대지 않고 눌러도 만료일이 조용히 바뀐다는
            QA 지적(`w6-qa-call-screen-fixes` Q-63)에 맞춰 결과 날짜를 미리 보여준다. */}
        <span className="admin-meta admin-entry-extend-preview">
          → {previewExpiryDate(months)} 로
        </span>
        <button
          type="button"
          className="btn-outline admin-release"
          disabled={!reasonFilled}
          onClick={() => {
            onExtend(months, reason.trim());
            setReason("");
          }}
        >
          재설정
        </button>
        <button
          type="button"
          className="btn-outline admin-release"
          disabled={!reasonFilled}
          onClick={() => {
            onRelease(reason.trim());
            setReason("");
          }}
        >
          해제
        </button>
      </div>
      {history.status === "loading" ? (
        <p className="admin-meta">변경 이력을 불러오는 중...</p>
      ) : null}
      {history.status === "error" ? (
        <p className="header-error" role="alert">
          {history.message}
        </p>
      ) : null}
      {history.status === "ready" ? (
        history.changes.length === 0 ? (
          <p className="admin-empty">변경 이력 없음</p>
        ) : (
          <ul className="admin-list is-muted">
            {history.changes.map((change) => (
              <li key={change.change_id}>
                <span className="admin-meta">
                  {new Date(change.previous_expires_at).toLocaleDateString("ko-KR")} →{" "}
                  {new Date(change.new_expires_at).toLocaleDateString("ko-KR")} ·{" "}
                  {change.changed_by} · {change.reason} ·{" "}
                  {new Date(change.changed_at).toLocaleString("ko-KR")}
                </span>
              </li>
            ))}
          </ul>
        )
      ) : null}
    </li>
  );
}
