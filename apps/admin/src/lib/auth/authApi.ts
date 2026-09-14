/**
 * server(FastAPI) `/admin/auth/*` 호출. 회원가입 엔드포인트는 없다 — 구글 id_token
 * 하나로 로그인이 끝난다. 응답의 숫자 필드는 서버 쪽 7.3절 계약(`StrField`)에 따라
 * 문자열로 온다 — 여기서 숫자로 되돌린다(요청 계약이 아니라 이 클라이언트의 편의를 위해서다).
 */
export function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  if (configured !== undefined && configured.length > 0) {
    return configured.replace(/\/$/, "");
  }
  return import.meta.env.DEV ? "http://localhost:8000" : "";
}

export interface TokenPair {
  accessToken: string;
  accessTokenExpiresIn: number;
  refreshToken: string;
  refreshTokenExpiresIn: number;
}

export interface AdminMe {
  email: string;
  name: string | null;
}

export class AdminAuthApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new AdminAuthApiError(
      (detail && typeof detail.detail === "string" && detail.detail) || `요청 실패 (${response.status})`,
      response.status,
    );
  }
  return (await response.json()) as T;
}

function toTokenPair(raw: {
  access_token: string;
  access_token_expires_in: string;
  refresh_token: string;
  refresh_token_expires_in: string;
}): TokenPair {
  return {
    accessToken: raw.access_token,
    accessTokenExpiresIn: Number(raw.access_token_expires_in),
    refreshToken: raw.refresh_token,
    refreshTokenExpiresIn: Number(raw.refresh_token_expires_in),
  };
}

export async function loginWithGoogle(idToken: string): Promise<TokenPair> {
  return toTokenPair(await postJson("/admin/auth/google", { id_token: idToken }));
}

export async function refreshTokenPair(refreshToken: string): Promise<TokenPair> {
  return toTokenPair(await postJson("/admin/auth/refresh", { refresh_token: refreshToken }));
}

export async function logoutRequest(accessToken: string, refreshToken: string | null): Promise<void> {
  await fetch(`${apiBaseUrl()}/admin/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ refresh_token: refreshToken }),
  }).catch(() => {
    // 로그아웃은 최선을 다할 뿐이다 — 네트워크가 끊겨도 프론트 상태는 지운다(아래 authStore).
  });
}

export async function fetchMe(accessToken: string): Promise<AdminMe> {
  const response = await fetch(`${apiBaseUrl()}/admin/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new AdminAuthApiError("세션이 유효하지 않다", response.status);
  }
  const body = (await response.json()) as { email: string; name: string | null };
  return body;
}
