import { useEffect, useRef, type ReactElement } from "react";
import { useAuthStore } from "../lib/auth/authStore";

/**
 * 관리자 로그인 화면. 회원가입 폼이 없다 — 구글 버튼 하나뿐이다(2026-09-14).
 * 구글이 인증한 이메일이 `admin_account`(RDS)에 없으면 로그인 자체가 403 으로 거절된다.
 */
export function AdminLoginScreen(): ReactElement {
  const buttonHostRef = useRef<HTMLDivElement>(null);
  const loginWithGoogleIdToken = useAuthStore((s) => s.loginWithGoogleIdToken);
  const status = useAuthStore((s) => s.status);
  const error = useAuthStore((s) => s.error);

  useEffect(() => {
    const clientId: string = import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID ?? "";
    if (clientId.length === 0) {
      return; // 아래 화면에 안내 문구를 띄운다
    }

    let cancelled = false;
    let attempts = 0;

    function tryInit(): void {
      if (cancelled) {
        return;
      }
      if (window.google?.accounts?.id && buttonHostRef.current) {
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => {
            void loginWithGoogleIdToken(response.credential);
          },
        });
        window.google.accounts.id.renderButton(buttonHostRef.current, {
          theme: "outline",
          size: "large",
          text: "signin_with",
          width: 280,
        });
        return;
      }
      attempts += 1;
      if (attempts < 50) {
        // gsi/client 스크립트(index.html)가 아직 로드 중일 수 있다 — 최대 5초 재시도
        setTimeout(tryInit, 100);
      }
    }

    tryInit();
    return () => {
      cancelled = true;
    };
  }, [loginWithGoogleIdToken]);

  const clientIdMissing = !import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID;

  return (
    <div className="admin-login-screen">
      <div className="admin-login-card">
        <h1 className="admin-login-title">CallGuard 관리자</h1>
        <p className="admin-login-subtitle">구글 계정으로 로그인한다. 회원가입은 없다 — 관리자로 등록된 계정만 들어올 수 있다.</p>

        {clientIdMissing ? (
          <p className="admin-login-error">
            VITE_GOOGLE_OAUTH_CLIENT_ID 가 설정되지 않았다 — .env.local 을 확인하라.
          </p>
        ) : (
          <div ref={buttonHostRef} className="admin-login-google-button" />
        )}

        {status === "authenticating" ? <p className="admin-login-status">로그인하는 중…</p> : null}
        {error !== null ? <p className="admin-login-error">{error}</p> : null}
      </div>
    </div>
  );
}
