import { useMemo, type ReactElement } from "react";
import type { KnowledgeGapEntry } from "../../types/blacklist";

interface GapRow {
  query: string;
  missCount: number;
  totalCount: number;
  callIds: string[];
}

/**
 * 지식베이스 갭 관리. Zendesk Guide Admin·Intercom의 "콘텐츠 갭" 리포트를
 * 본떴다 — D-4(공백 리포트)는 지금까지 통화 1건 단위(`CallSummaryPanel`)로만
 * 보였는데, 여러 통화에 걸쳐 모아야 "어떤 질문이 자주 안 잡히는지" 우선순위가
 * 보인다. 판정을 새로 하지 않는다 — `knowledgeGapLog`(상담원이 직접 검색한 기록)를
 * 질의 기준으로 묶어 세기만 한다.
 */
export function KnowledgeGapTab({
  log,
}: {
  log: KnowledgeGapEntry[];
}): ReactElement {
  const rows = useMemo<GapRow[]>(() => {
    const byQuery = new Map<string, GapRow>();
    for (const entry of log) {
      const key = entry.query.trim();
      if (key.length === 0) {
        continue;
      }
      const row = byQuery.get(key) ?? {
        query: key,
        missCount: 0,
        totalCount: 0,
        callIds: [],
      };
      row.totalCount += 1;
      if (!entry.found) {
        row.missCount += 1;
      }
      if (!row.callIds.includes(entry.call_id)) {
        row.callIds.push(entry.call_id);
      }
      byQuery.set(key, row);
    }
    return [...byQuery.values()]
      .filter((row) => row.missCount > 0)
      .sort((a, b) => b.missCount - a.missCount || b.totalCount - a.totalCount);
  }, [log]);

  if (rows.length === 0) {
    return (
      <section aria-label="지식베이스 갭">
        <p className="admin-empty">
          아직 검색 실패로 기록된 질의가 없습니다. 상담원이 직접 검색해
          못 찾은 질의가 여기 쌓입니다.
        </p>
      </section>
    );
  }

  return (
    <section aria-label="지식베이스 갭">
      <p className="admin-help">
        상담원이 직접 검색했는데 문서를 못 찾은 질의를 모은 것입니다. 자동
        추천이 놓친 것은 화면 밖이라 여기 안 잡힙니다 — 상담원이 관찰한
        범위만 집계됩니다.
      </p>
      <ul className="gap-rank-list">
        {rows.map((row) => (
          <li key={row.query} className="gap-rank-item">
            <span className="gap-rank-query">{row.query}</span>
            <span className="gap-rank-count">
              실패 {row.missCount}/{row.totalCount}건 · 통화 {row.callIds.length}건
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
