// Requirement: D-1, SEC-2
/**
 * `--close`(`POST /hub/calls/{id}/close`)에 실을 토큰을 고른다 — 서버 문은 `hub/dependencies/close_guard.py`(`decisions/315`).
 *
 * 그 문은 **상담원 토큰**(`cga_…`, `agent_token` 해시로 확인) 또는 **서비스 토큰**(서버 `INGEST_SERVICE_TOKEN` 과 같은 값) 중
 * 하나를 받는다. 서비스 토큰이 서버에 설정되지 않은 곳(로컬 E2E)에서는 상담원 토큰만 통한다 — 전에는 `CORE_API_TOKEN` 만 실어
 * 로컬 `--close` 가 401 이었다(2026-09-22 QA).
 *
 * - `CALL_AGENT_TOKEN` 이 있으면 그것(대시보드 `apps/call` 의 `coreClient.ts` 가 `/close` 에 싣는 것과 같은 종류)
 * - 없으면 `CORE_API_TOKEN`(서비스 토큰)
 * **헤더로만 싣는다.** 명령줄 인자로 받지 않고(셸 기록), 값은 어디에도 찍지 않는다 — 돌려주는 `source` 는 변수 **이름**뿐이다.
 */

export const ENV_AGENT_TOKEN = "CALL_AGENT_TOKEN";
export const ENV_SERVICE_TOKEN = "CORE_API_TOKEN";

export interface CloseAuth {
  headers: Record<string, string>;
  /** 어느 환경변수에서 왔는가(이름만). 없으면 null */
  source: string | null;
}

export function closeAuth(env: Record<string, string | undefined>): CloseAuth {
  for (const name of [ENV_AGENT_TOKEN, ENV_SERVICE_TOKEN]) {
    const value = (env[name] ?? "").trim();
    if (value !== "") {
      return { headers: { authorization: `Bearer ${value}` }, source: name };
    }
  }
  return { headers: {}, source: null };
}
