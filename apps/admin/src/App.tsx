import type { ReactElement } from "react";
import { AdminPanel } from "./components/AdminPanel";
import { dashboardUrl } from "./lib/dashboardUrl";

/**
 * 관리자 앱 진입점. 2026-09-10 — 상담원 대시보드(`apps/dashboard`)와
 * 완전히 분리된 별도 앱이다(포트 5174). 버튼으로 오가지 않는다.
 */
export function App(): ReactElement {
  return (
    <div className="app-viewport">
      <div className="app-shell">
        <AdminPanel
          onExit={() => {
            window.location.href = dashboardUrl();
          }}
        />
      </div>
    </div>
  );
}
