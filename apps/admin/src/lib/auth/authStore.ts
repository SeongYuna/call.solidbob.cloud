import { create } from "zustand";
import { AdminAuthApiError, fetchMe, loginWithGoogle, logoutRequest, refreshTokenPair } from "./authApi";

/**
 * 관리자 로그인 상태. 회원가입 화면이 없다 — 구글 로그인 하나로 끝난다(2026-09-14).
 *
 * access token 은 메모리(zustand state)에만 둔다 — 새로고침하면 사라진다.
 * refresh token 만 localStorage 에 남겨서, 새로고침 직후 `restoreSession()`이 그것으로
 * 조용히 새 access token 을 받아온다. 만료(10분, 테스트 스코프)가 짧아서 오래 묵은
 * refresh token 은 새로고침해도 어차피 서버가 401 로 거절한다 — 그러면 로그인 화면으로 되돌아간다.
 */

const REFRESH_TOKEN_STORAGE_KEY = "callguard-admin-refresh-token";
// access token 만료 30초 전에 미리 갱신한다 — 정확히 만료 시점에 요청이 걸리면 그 요청이 401 난다.
const REFRESH_MARGIN_MS = 30_000;

type Status = "anonymous" | "authenticating" | "authenticated";

interface AdminIdentity {
  email: string;
  name: string | null;
}

interface AuthState {
  status: Status;
  accessToken: string | null;
  admin: AdminIdentity | null;
  error: string | null;
  loginWithGoogleIdToken: (idToken: string) => Promise<void>;
  restoreSession: () => Promise<void>;
  logout: () => Promise<void>;
}

let refreshTimer: ReturnType<typeof setTimeout> | null = null;

function clearRefreshTimer(): void {
  if (refreshTimer !== null) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}

function readStoredRefreshToken(): string | null {
  try {
    return window.localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
  } catch {
    return null; // 프라이빗 모드 등에서 localStorage 가 막혀 있을 수 있다
  }
}

function storeRefreshToken(token: string | null): void {
  try {
    if (token === null) {
      window.localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    } else {
      window.localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
    }
  } catch {
    // 저장 못 해도 로그인 자체는 이번 세션에서 동작한다 — 새로고침 유지만 안 될 뿐
  }
}

export const useAuthStore = create<AuthState>((set, get) => {
  function scheduleRefresh(expiresInSeconds: number): void {
    clearRefreshTimer();
    const delay = Math.max(expiresInSeconds * 1000 - REFRESH_MARGIN_MS, 1_000);
    refreshTimer = setTimeout(() => {
      void silentRefresh();
    }, delay);
  }

  async function silentRefresh(): Promise<void> {
    const refreshToken = readStoredRefreshToken();
    if (refreshToken === null) {
      set({ status: "anonymous", accessToken: null, admin: null });
      return;
    }
    try {
      const pair = await refreshTokenPair(refreshToken);
      storeRefreshToken(pair.refreshToken);
      const me = await fetchMe(pair.accessToken);
      set({ status: "authenticated", accessToken: pair.accessToken, admin: me, error: null });
      scheduleRefresh(pair.accessTokenExpiresIn);
    } catch {
      // refresh token 도 만료/무효 — 조용히 로그아웃 상태로. 사용자에게는 로그인 화면이 다시 뜬다.
      storeRefreshToken(null);
      clearRefreshTimer();
      set({ status: "anonymous", accessToken: null, admin: null });
    }
  }

  return {
    status: "anonymous",
    accessToken: null,
    admin: null,
    error: null,

    async loginWithGoogleIdToken(idToken: string) {
      set({ status: "authenticating", error: null });
      try {
        const pair = await loginWithGoogle(idToken);
        storeRefreshToken(pair.refreshToken);
        const me = await fetchMe(pair.accessToken);
        set({ status: "authenticated", accessToken: pair.accessToken, admin: me, error: null });
        scheduleRefresh(pair.accessTokenExpiresIn);
      } catch (err) {
        const message =
          err instanceof AdminAuthApiError && err.status === 403
            ? "관리자로 등록되지 않은 구글 계정이다."
            : "로그인에 실패했다. 다시 시도하라.";
        set({ status: "anonymous", accessToken: null, admin: null, error: message });
      }
    },

    async restoreSession() {
      if (readStoredRefreshToken() === null) {
        return;
      }
      await silentRefresh();
    },

    async logout() {
      const { accessToken } = get();
      const refreshToken = readStoredRefreshToken();
      clearRefreshTimer();
      storeRefreshToken(null);
      set({ status: "anonymous", accessToken: null, admin: null, error: null });
      if (accessToken !== null) {
        await logoutRequest(accessToken, refreshToken);
      }
    },
  };
});
