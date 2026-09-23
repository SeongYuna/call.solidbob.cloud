import { useMemo, type ReactElement } from "react";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

/**
 * 현황판. Genesys Cloud·NICE CXone류 콜센터 관리자 도구의 "실시간 대시보드"를
 * 본떴다 — 다만 **상담원 이름을 붙인 개인별 지표는 넣지 않는다**(부록 B
 * "개인별 지표는 본인만 열람, 관리자 미노출" 원칙과 방향이 같다). 전부 셀 수
 * 있는 누적 건수다.
 *
 * ⚠ `apps/admin`은 상담원 대시보드와 완전히 분리된 별도 앱이라(2026-09-10)
 * "지금 진행 중인 통화" 같은 실시간 신호는 여기서 알 수 없다.
 *
 * 2026-09-22 — `GET /hub/admin-stats` 하나로 네 지표를 전부 받는다
 * (`store/adminStore.ts`의 `loadAll`). 예전엔 목록 API를 `limit=1`로 불러
 * `total`만 뽑거나(완료 통화·콜가드) 클라이언트에서 목록을 세는(승인 대기·
 * 활성 등록) 방식이었다 — mock 시드값이 아니라 그때도 이미 실제 값이었지만,
 * 호출이 넷으로 흩어져 있었다. `countedAt`은 서버가 그 값을 센 시각이다 —
 * `loadAll` 시점의 스냅샷이라 그 사이 승인·해제해도 다시 부르기 전까진
 * 안 바뀐다.
 *
 * 2026-09-15 — 좌측 통계 카드 4개(그대로) + 우측 비율 도넛 차트로 재설계했다.
 * 새 지표를 만들지 않는다 — 기존 4개 값의 **비중**만 다르게 보여줄 뿐이다.
 *
 * 2026-09-22(2차) — J-5 배정 판정 집계 세 칸을 **별도 섹션**으로 더했다(도넛에는
 * 안 섞는다 — 위 "새 지표를 만들지 않는다"는 저 도넛 하나에 한정된 약속이고,
 * J-5는 그날 처음 실제로 값이 쌓이기 시작한 새 기능이라 기존 네 지표와 성격이
 * 다르다). `admin-stats` 응답엔 처음부터 있었지만 콜 미디에이터가 안 불러
 * 전부 0이던 동안은 렌더하지 않았다 — `decisions/126`·`320` 배포(call-mediator
 * 0.2.5) 뒤에 연다.
 */
export function WallboardTab({
  completedCallsTotal,
  callGuardTotal,
  pendingRequestCount,
  activeEntryCount,
  countedAt,
  routingDecisions,
  routingBlacklisted,
  routingFellBack,
}: {
  completedCallsTotal: number;
  callGuardTotal: number;
  pendingRequestCount: number;
  activeEntryCount: number;
  /** `GET /hub/admin-stats`의 `counted_at` — 아직 못 불렀으면 null. */
  countedAt: string | null;
  /** J-5 배정 판정 전체 건수(`routing_log`). 콜 미디에이터가 안 붙었으면 0. */
  routingDecisions: number;
  /** 그중 블랙리스트 등록 고객이었던 건수. */
  routingBlacklisted: number;
  /** 그중 근속 기준 상담사가 없어 일반 배정으로 떨어진 건수. */
  routingFellBack: number;
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
        {countedAt !== null
          ? `${new Date(countedAt).toLocaleString("ko-KR")} 기준입니다.`
          : "집계 시각을 아직 불러오지 못했습니다."}{" "}
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

      <section className="wallboard-j5" aria-label="배정 판정(J-5)" style={{ marginTop: 20 }}>
        <h3 className="wallboard-donut-title">배정 판정(J-5)</h3>
        {routingDecisions === 0 ? (
          <p className="admin-empty">아직 판정된 통화가 없습니다.</p>
        ) : (
          <div className="wallboard-grid">
            <WallboardTile label="배정 판정 전체" value={routingDecisions} />
            <WallboardTile
              label="블랙리스트 고객"
              value={routingBlacklisted}
              emphasize={routingBlacklisted > 0}
            />
            <WallboardTile label="일반 배정으로 전환" value={routingFellBack} />
          </div>
        )}
      </section>
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
