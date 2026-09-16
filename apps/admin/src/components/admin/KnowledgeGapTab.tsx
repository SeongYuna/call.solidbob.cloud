import { useMemo, useState, type ReactElement } from "react";
import type { KnowledgeGapItem } from "../../lib/api/hubClient";

const MODULE_LABEL: Record<KnowledgeGapItem["module"], string> = {
  B: "B · 검색 실패",
  C: "C · 놓친 위반",
  F: "F · 사후 문제",
};

type GapFilter = "all" | "open" | "resolved";

/**
 * 지식베이스 갭 관리. D-4(공백 리포트) 실제 계약(`GET /hub/knowledge-gaps`)에 붙인다.
 *
 * 2026-09-16 재설계 — 옛 화면은 상담원이 직접 검색해 못 찾은 질의(`{query, found}`)를
 * 질의 기준으로 묶어 세는 mock 전용이었다. 실제 계약은 그보다 넓은 D-4 개념
 * (`{module: B|C|F, description, status}`)이라 필드가 대응되지 않아 다시 짰다 —
 * B(검색 실패)·C(놓친 위반)·F(통과했으나 사후 문제) 세 갈래를 module 뱃지로 구분하고,
 * 항목마다 해제(resolved)/다시 열기(open) 버튼을 둔다. 서버가 되돌리기도 허용한다
 * (`GapResolutionRequest` — 잘못 닫은 것을 기록에서 지우지 않는다, 절대 원칙 8).
 */
export function KnowledgeGapTab({
  gaps,
  onResolve,
}: {
  gaps: KnowledgeGapItem[];
  onResolve: (gapId: string, status: "open" | "resolved") => void;
}): ReactElement {
  const [filter, setFilter] = useState<GapFilter>("open");

  const openCount = gaps.filter((g) => g.status === "open").length;
  const resolvedCount = gaps.length - openCount;
  const filtered = useMemo(() => {
    const rows = gaps.filter((g) => filter === "all" || g.status === filter);
    return [...rows].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
  }, [gaps, filter]);

  if (gaps.length === 0) {
    return (
      <section aria-label="지식베이스 갭">
        <p className="admin-empty">
          아직 쌓인 공백 신고가 없습니다. 검색 실패(B)·놓친 위반(C)·사후 문제(F)가
          여기 모입니다.
        </p>
      </section>
    );
  }

  return (
    <section aria-label="지식베이스 갭">
      <p className="admin-help">
        B(검색 실패) · C(놓친 위반) · F(통과했으나 사후 문제)를 한 곳에 모은 공백
        리포트입니다. 판정을 새로 하지 않습니다 — 서버가 기록한 것을 그대로 보여줍니다.
      </p>
      <div className="admin-tabs admin-subfilter" role="tablist" aria-label="열림·해제 분류">
        <FilterChip label="전체" count={gaps.length} active={filter === "all"} onClick={() => setFilter("all")} />
        <FilterChip label="열림" count={openCount} active={filter === "open"} onClick={() => setFilter("open")} />
        <FilterChip
          label="해제됨"
          count={resolvedCount}
          active={filter === "resolved"}
          onClick={() => setFilter("resolved")}
        />
      </div>
      {filtered.length === 0 ? (
        <p className="admin-empty">
          {filter === "open" ? "열려 있는 공백이 없습니다." : "해제된 공백이 없습니다."}
        </p>
      ) : (
        <ul className="admin-list">
          {filtered.map((gap) => (
            <GapRow key={gap.gap_id} gap={gap} onResolve={onResolve} />
          ))}
        </ul>
      )}
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

function GapRow({
  gap,
  onResolve,
}: {
  gap: KnowledgeGapItem;
  onResolve: (gapId: string, status: "open" | "resolved") => void;
}): ReactElement {
  const resolved = gap.status === "resolved";
  return (
    <li className={`admin-entry-row${resolved ? " is-muted" : ""}`}>
      <div className="admin-entry-row-main">
        <span className={`admin-module-badge module-${gap.module.toLowerCase()}`}>
          {MODULE_LABEL[gap.module]}
        </span>
        <span className="admin-ref">{gap.description}</span>
        <span className="admin-meta">
          {new Date(gap.created_at).toLocaleDateString("ko-KR")}
          {gap.call_id !== null ? ` · ${gap.call_id}` : ""}
        </span>
      </div>
      <div className="admin-entry-row-actions">
        <button
          type="button"
          className="btn-outline admin-release"
          onClick={() => {
            onResolve(gap.gap_id, resolved ? "open" : "resolved");
          }}
        >
          {resolved ? "다시 열기" : "해제"}
        </button>
      </div>
    </li>
  );
}
