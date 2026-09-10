import type { ReactElement } from "react";

/**
 * 현황판. Genesys Cloud·NICE CXone류 콜센터 관리자 도구의 "실시간 대시보드"를
 * 본떴다 — 다만 **상담원 이름을 붙인 개인별 지표는 넣지 않는다**(부록 B
 * "개인별 지표는 본인만 열람, 관리자 미노출" 원칙과 방향이 같다). 전부 셀 수
 * 있는 누적 건수다.
 *
 * ⚠ `apps/admin`은 상담원 대시보드와 완전히 분리된 별도 앱이라(2026-09-10)
 * "지금 진행 중인 통화" 같은 실시간 신호는 여기서 알 수 없다. 지금은
 * `store/adminStore.ts`의 mock 시드 값 + 이 세션에서 처리한 것만 보여준다 —
 * 백엔드가 붙으면 조회 API로 바꾼다.
 */
export function WallboardTab({
  completedCallsTotal,
  callGuardTotal,
  pendingRequestCount,
  activeEntryCount,
}: {
  completedCallsTotal: number;
  callGuardTotal: number;
  pendingRequestCount: number;
  activeEntryCount: number;
}): ReactElement {
  return (
    <section aria-label="현황판">
      <p className="admin-help">
        백엔드 연동 전이라 mock 시드 값 + 이 세션에서 처리한 건수입니다.
        실시간 통화 현황(지금 몇 통화가 진행 중인지)은 상담원 앱과 분리돼
        있어 여기서 볼 수 없습니다.
      </p>
      <div className="wallboard-grid">
        <WallboardTile label="완료 통화 누적" value={completedCallsTotal} />
        <WallboardTile label="콜가드 경고 누적" value={callGuardTotal} />
        <WallboardTile
          label="승인 대기 요청"
          value={pendingRequestCount}
          emphasize={pendingRequestCount > 0}
        />
        <WallboardTile label="활성 블랙리스트 등록" value={activeEntryCount} />
      </div>
    </section>
  );
}

function WallboardTile({
  label,
  value,
  emphasize,
}: {
  label: string;
  value: number;
  emphasize?: boolean;
}): ReactElement {
  return (
    <div className={emphasize === true ? "wallboard-tile is-watch" : "wallboard-tile"}>
      <p className="wallboard-tile-label">{label}</p>
      <span className="wallboard-tile-num">{value}</span>
    </div>
  );
}
