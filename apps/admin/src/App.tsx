import { useEffect, type ReactElement } from "react";
import { AdminLoginScreen } from "./components/AdminLoginScreen";
import { AdminPanel } from "./components/AdminPanel";
import { useAuthStore } from "./lib/auth/authStore";

/**
 * 관리자 앱 진입점. 2026-09-10 — 상담원 대시보드(`apps/call`)와
 * 완전히 분리된 별도 앱이다(포트 5174). 버튼으로 오가지 않는다 —
 * 2026-09-14 "상담 화면으로" 버튼도 없앴다(사용자 지시).
 *
 * 2026-09-14 — 구글 로그인 게이트를 추가했다. 회원가입 화면은 없다:
 * 로그인 안 됨 → AdminLoginScreen, 로그인 됨 → AdminPanel.
 */
export function App(): ReactElement {
  const status = useAuthStore((s) => s.status);
  const admin = useAuthStore((s) => s.admin);
  const restoreSession = useAuthStore((s) => s.restoreSession);
  const logout = useAuthStore((s) => s.logout);

  useEffect(() => {
    void restoreSession(); // 새로고침 직후 저장된 refresh token으로 조용히 재로그인 시도
  }, [restoreSession]);

  return (
    <div className="app-viewport">
      <div className="app-shell">
        {status === "authenticated" && admin !== null ? (
          <AdminPanel
            adminName={admin.name ?? admin.email}
            onLogout={() => {
              void logout();
            }}
          />
        ) : (
          <AdminLoginScreen />
        )}
      </div>
    </div>
  );
}
