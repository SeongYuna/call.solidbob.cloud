/**
 * 상담원 대시보드(`apps/dashboard`) 주소. 두 앱이 완전히 분리돼 있어 고정
 * 상수로 굳히지 않는다 — 운영 주소는 배포마다 다르다(`.claude/rules/dashboard.md`
 * "운영 주소를 개발 기본값으로 굳히지 않는다"). 개발 중에만 로컬 기본값을 쓴다.
 */
export function dashboardUrl(): string {
  const configured = import.meta.env.VITE_DASHBOARD_URL;
  if (configured !== undefined && configured.length > 0) {
    return configured;
  }
  return import.meta.env.DEV ? "http://localhost:5173/" : "/";
}
