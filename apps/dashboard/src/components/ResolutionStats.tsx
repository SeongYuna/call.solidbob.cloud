/**
 * 이 패널은 팀 결정이 아닌 개인 판단으로 추가됨(2026-08-31).
 * 제거 시 이 파일과 호출부 한 줄만 지우면 된다.
 */
import { useMemo, type ReactElement } from "react";
import { listCallHistoryRows } from "../mock/callHistory";
import { demoResolutionFlags } from "../mock/resolution";

/** 끄려면 false. CallHistoryPanel 의 조건부 렌더가 이걸 본다. */
export const SHOW_RESOLUTION_STATS = true;

export function ResolutionStats(): ReactElement {
  const rows = useMemo(() => listCallHistoryRows(), []);
  const resolvedFlags = useMemo(() => demoResolutionFlags(rows), [rows]);
  const resolvedCount = resolvedFlags.filter(Boolean).length;

  return (
    <p className="call-history-stats">
      <span>
        {`해결률 ${resolvedCount}/${rows.length}건 (데모 데이터 기준)`}
      </span>
      <span className="resolve-dots" aria-hidden="true">
        {resolvedFlags.map((ok, index) => (
          <span
            key={rows[index]?.item.call_id ?? index}
            className={`resolve-dot${ok ? " is-ok" : " is-open"}`}
          />
        ))}
      </span>
    </p>
  );
}
