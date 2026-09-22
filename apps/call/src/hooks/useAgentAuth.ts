import { useCallback, useEffect, useState } from "react";
import { CoreApiError, fetchAgentMe, isCoreApiConfigured } from "../lib/api/coreClient";
import {
  captureAgentTokenFromUrl,
  clearAgentToken,
  readAgentToken,
  writeAgentToken,
} from "../lib/agentToken";

/**
 * 상담원 로그인 상태. 실서버(`VITE_CORE_API_URL`)가 없으면 인증할 대상 자체가 없으므로
 * 로그인 화면 없이 바로 들여보낸다 — 공개 mock 데모는 지금처럼 계속 열려 있다.
 * 실서버가 있으면 토큰을 `GET /hub/agents/me`(`decisions/307`)로 검증하고, 실패하면
 * 로그인 화면으로 돌려보낸다.
 */
export type AgentAuthStatus = "checking" | "authenticated" | "unauthenticated";

export interface AgentAuthState {
  status: AgentAuthStatus;
  agentId: string | null;
  displayName: string | null;
  error: string | null;
  login: (token: string) => Promise<boolean>;
  logout: () => void;
}

export function useAgentAuth(): AgentAuthState {
  const [status, setStatus] = useState<AgentAuthStatus>(() =>
    isCoreApiConfigured() ? "checking" : "authenticated",
  );
  const [agentId, setAgentId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isCoreApiConfigured()) {
      return;
    }
    captureAgentTokenFromUrl();
    const token = readAgentToken();
    if (token === null) {
      setStatus("unauthenticated");
      return;
    }
    let cancelled = false;
    fetchAgentMe(token)
      .then(({ agentId: id, displayName: name }) => {
        if (cancelled) {
          return;
        }
        setAgentId(id);
        setDisplayName(name);
        setStatus("authenticated");
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return;
        }
        // 토큰이 오래 남으므로 서버가 무효(401·403 — 폐기·없는 토큰)라고 답했을 때만 지운다.
        // 네트워크 끊김·서버 5xx 로 지우면 잠깐의 장애가 재로그인 요구로 번진다.
        if (err instanceof CoreApiError && (err.status === 401 || err.status === 403)) {
          clearAgentToken();
        }
        setError(err instanceof Error ? err.message : "로그인 확인에 실패했다.");
        setStatus("unauthenticated");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (token: string): Promise<boolean> => {
    const trimmed = token.trim();
    if (trimmed.length === 0) {
      setError("토큰을 입력해 주세요.");
      return false;
    }
    try {
      const { agentId: id, displayName: name } = await fetchAgentMe(trimmed);
      writeAgentToken(trimmed);
      setAgentId(id);
      setDisplayName(name);
      setError(null);
      setStatus("authenticated");
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인에 실패했다.");
      return false;
    }
  }, []);

  const logout = useCallback((): void => {
    clearAgentToken();
    setAgentId(null);
    setDisplayName(null);
    setError(null);
    setStatus("unauthenticated");
  }, []);

  return { status, agentId, displayName, error, login, logout };
}
