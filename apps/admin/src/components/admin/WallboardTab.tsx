import { useMemo, type ReactElement } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

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
 *
 * 2026-09-15 — 좌측 통계 카드 4개(그대로) + 우측 비율 도넛 차트로 재설계했다.
 * 새 지표를 만들지 않는다 — 기존 4개 값의 **비중**만 다르게 보여줄 뿐이다.
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
  const slices = useMemo(
    () => [
      { key: "completed", label: "완료 통화 누적", value: completedCallsTotal, color: "var(--accent)" },
      { key: "guard", label: "콜가드 경고 누적", value: callGuardTotal, color: "var(--keyword)" },
      { key: "pending", label: "승인 대기 요청", value: pendingRequestCount, color: "var(--pii)" },
      { key: "entries", label: "활성 블랙리스트 등록", value: activeEntryCount, color: "var(--dim)" },
    ],
    [completedCallsTotal, callGuardTotal, pendingRequestCount, activeEntryCount],
  );
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);

  return (
    <section aria-label="현황판">
      <p className="admin-help">
        백엔드 연동 전이라 mock 시드 값 + 이 세션에서 처리한 건수입니다.
        실시간 통화 현황(지금 몇 통화가 진행 중인지)은 상담원 앱과 분리돼
        있어 여기서 볼 수 없습니다.
      </p>
      <div className="wallboard-layout">
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

        <div className="wallboard-donut">
          <h3 className="wallboard-donut-title">네 지표 비율</h3>
          {total === 0 ? (
            <p className="admin-empty">데이터가 없습니다.</p>
          ) : (
            <>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={slices}
                    dataKey="value"
                    nameKey="label"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={2}
                    stroke="none"
                    isAnimationActive={false}
                  >
                    {slices.map((slice) => (
                      <Cell key={slice.key} fill={slice.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: unknown) => [`${String(value)}건`, ""]} />
                </PieChart>
              </ResponsiveContainer>
              <ul className="wallboard-donut-legend">
                {slices.map((slice) => (
                  <li key={slice.key}>
                    <span className="wallboard-donut-swatch" style={{ background: slice.color }} />
                    <span>{slice.label}</span>
                    <strong>{slice.value}</strong>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
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
