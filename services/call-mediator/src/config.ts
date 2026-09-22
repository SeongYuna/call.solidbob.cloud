// Requirement: SEC-2, COST-1
/**
 * `process.env` 를 읽는 **유일한 곳** — 서버 `core/config.py` 와 같은 규칙이다.
 *
 * | 키 | 쓰임 | 없으면 |
 * |---|---|---|
 * | `CALL_MEDIATOR_PORT` | 듣는 포트 | 8080 |
 * | `CORE_API_URL` | server 주소. 운영은 `http://callguard-server` | `http://localhost:8000` |
 * | `CORE_API_TOKEN` | server 쓰기 경로의 서비스 토큰 — server 의 `INGEST_SERVICE_TOKEN` 과 **같은 값**(`decisions/120`) | 헤더를 보내지 않는다 |
 * | `ROUTING_CANDIDATES` | J-5 배정 판정에 넘길 상담사 `agent_id` 쉼표 목록 — 시연용. 미디에이터는 대기 상태를 모른다(`decisions/126`) | 빈 목록(서버가 기존 배정 규칙으로) |
 * | `GOOGLE_APPLICATION_CREDENTIALS` | 서비스 계정 키 **파일 경로** (라이브러리가 직접 읽는다) | 채널을 열지 않는다 |
 * | `STT_MAX_SECONDS_PER_DAY` · `_MONTH` | COST-1 2차 캡 | 채널을 열지 않는다 (fail-closed) |
 * | `CORS_ALLOWED_ORIGINS` | 대시보드 `Origin` 허용 목록 — 서버와 같은 키·같은 기본값 | 로컬 Vite 둘 |
 * | `CALL_MEDIATOR_INGEST_TOKEN` | `/ingest`(과금) — 진짜 비밀, 생산자만 (`domain/access.ts`) | **이 머신(루프백) 접속만 받는다** |
 * | `CALL_MEDIATOR_VIEW_TOKEN` | `/ws`(자막 보기) — 브라우저가 내므로 비밀이 아니다 | **이 머신(루프백) 접속만 받는다** |
 *
 * ⚠ `CALL_MEDIATOR_PORT`·`CORE_API_URL`·`CALL_MEDIATOR_INGEST_TOKEN`·`CALL_MEDIATOR_VIEW_TOKEN` 은 아직 `.env.example` 에 없다 — 그 파일은 자격증명 보호 훅이
 * 편집을 막아 사람이 직접 채운다(`server/CLAUDE.md` §6 과 같은 처지).
 */
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import type { Caps } from "./domain/budget.ts";

export interface CallMediatorConfig {
  port: number;
  coreApiUrl: string;
  /** server 쓰기 경로의 서비스 토큰. 비어 있으면 `Authorization` 을 보내지 않는다(`decisions/120` 이행기). */
  coreApiToken: string;
  /** J-5 배정 판정 후보(`agent_id`). 비면 빈 목록을 보낸다. */
  routingCandidates: string[];
  caps: Caps;
  allowedOrigins: string[];
  /** 문마다 토큰. 빈 문자열이면 설정되지 않았다. 값은 로그·`/health` 에 싣지 않는다. */
  tokens: { ingest: string; view: string };
  /** 키 파일이 실제로 있는가. 경로 자체는 밖에 싣지 않는다. */
  googleCredentialsReady: boolean;
  usageFile: string;
}

const LOCAL_VITE_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"];

/** `scripts/transcribe_batch.py` 의 `USAGE_FILE` 과 같은 파일 — 저장소 루트 기준. */
const USAGE_FILE = fileURLToPath(new URL("../../../data/processed/stt-usage.json", import.meta.url));

export function loadConfig(env: NodeJS.ProcessEnv = process.env): CallMediatorConfig {
  const credentials = (env.GOOGLE_APPLICATION_CREDENTIALS ?? "").trim();
  return {
    port: intOr(env.CALL_MEDIATOR_PORT, 8080),
    coreApiUrl: (env.CORE_API_URL ?? "").trim() || "http://localhost:8000",
    coreApiToken: (env.CORE_API_TOKEN ?? "").trim(),
    routingCandidates: csvOr(env.ROUTING_CANDIDATES, []),
    caps: {
      perDay: intOr(env.STT_MAX_SECONDS_PER_DAY, 0),
      perMonth: intOr(env.STT_MAX_SECONDS_PER_MONTH, 0),
    },
    allowedOrigins: csvOr(env.CORS_ALLOWED_ORIGINS, LOCAL_VITE_ORIGINS),
    tokens: {
      ingest: (env.CALL_MEDIATOR_INGEST_TOKEN ?? "").trim(),
      view: (env.CALL_MEDIATOR_VIEW_TOKEN ?? "").trim(),
    },
    googleCredentialsReady: credentials.length > 0 && existsSync(credentials),
    usageFile: USAGE_FILE,
  };
}

function intOr(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt((value ?? "").trim(), 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : fallback;
}

function csvOr(value: string | undefined, fallback: string[]): string[] {
  const items = (value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
  return items.length > 0 ? items : fallback;
}
