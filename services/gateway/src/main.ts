// Requirement: A-1, A-2, A-3, A-4, COST-1
/**
 * 합성 루트 — 설정을 읽고 어댑터를 꽂고 포트를 연다. 판정은 없다.
 *
 *   cd services/gateway && npm start        # ../../.env 를 읽는다 (셸 변수가 우선)
 *
 * 구글 키 파일이 없으면 서버는 뜨지만 `/ingest` 는 거절한다. 가짜 STT 로 조용히 대신하지 않는다 —
 * `call.stt_engine` 에 `google-stt` 라고 적힌 통화가 실제로는 가짜였다면 기록이 거짓이 된다.
 */
import { BudgetGuard } from "./app/budget_guard.ts";
import { CallRegistry } from "./app/call_registry.ts";
import type { Logger, SttEngine, SttHandlers, SttStream } from "./app/ports.ts";
import { GoogleSttEngine, googleStreamFactory } from "./adapters/google_stt.ts";
import { HttpHub } from "./adapters/hub_http.ts";
import { JsonLedgerFile } from "./adapters/ledger_file.ts";
import { DashboardHub, createGatewayServer } from "./adapters/ws_server.ts";
import { loadConfig } from "./config.ts";

const log: Logger = {
  info: (message) => console.log(`[gateway] ${message}`),
  warn: (message) => console.warn(`[gateway] ⚠ ${message}`),
};

/** 키가 없을 때 꽂는다. 채널을 열기 전에 거절된다 — 서버에 빈 통화 행을 만들지 않는다. */
class UnavailableStt implements SttEngine {
  readonly name = "google-stt";
  readonly unavailableReason = "GOOGLE_APPLICATION_CREDENTIALS 키 파일이 없다";

  open(_sampleRate: number, handlers: SttHandlers): SttStream {
    queueMicrotask(() => {
      handlers.onFatal(this.unavailableReason);
      handlers.onEnd();
    });
    return { write: () => {}, end: () => {} };
  }
}

const config = loadConfig();
const budget = new BudgetGuard(new JsonLedgerFile(config.usageFile), config.caps, () => new Date(), log);
const dashboards = new DashboardHub();
const stt: SttEngine = config.googleCredentialsReady ? new GoogleSttEngine(googleStreamFactory()) : new UnavailableStt();
const registry = new CallRegistry({
  hub: new HttpHub(config.coreApiUrl),
  stt,
  budget,
  broadcaster: dashboards,
  log,
  nowMs: () => Date.now(),
});

const server = createGatewayServer({
  registry,
  dashboards,
  allowedOrigins: config.allowedOrigins,
  tokens: config.tokens,
  log,
  health: () => {
    const usage = budget.snapshot();
    return {
      status: "ok",
      stt_engine: stt.name,
      stt_credentials_configured: config.googleCredentialsReady,
      stt_caps_configured: usage.capsConfigured,
      ingest_token_configured: config.tokens.ingest.length > 0,
      view_token_configured: config.tokens.view.length > 0,
      stt_used_today_seconds: usage.usedTodaySeconds,
      stt_cap_day_seconds: usage.capDay,
      stt_used_month_seconds: usage.usedMonthSeconds,
      stt_cap_month_seconds: usage.capMonth,
      active_calls: registry.activeCalls,
      dashboards: dashboards.size,
    };
  },
});

await budget.refresh();

server.listen(config.port, () => {
  log.info(`듣는 중 :${config.port} — /ingest(오디오) · /ws(대시보드) · /health`);
  if (!config.googleCredentialsReady) {
    log.warn("GOOGLE_APPLICATION_CREDENTIALS 키 파일이 없다 — /ingest 는 거절한다");
  }
  for (const [door, name] of [["ingest", "GATEWAY_INGEST_TOKEN"], ["view", "GATEWAY_VIEW_TOKEN"]] as const) {
    const token = config.tokens[door];
    if (token.length === 0) {
      log.warn(`${name} 이 없다 — 이 머신(루프백) 접속만 받는다. 밖에 열려면 넣는다`);
    } else if (door === "ingest" && token.length < 24) {
      log.warn(`${name} 이 24자보다 짧다 — 과금 문의 비밀이라 추측하기 어려워야 한다`);
    }
  }
  if (config.tokens.ingest.length > 0 && config.tokens.ingest === config.tokens.view) {
    log.warn("두 토큰이 같다 — 브라우저 번들에서 뽑은 값으로 과금 문(/ingest)이 열린다");
  }
  if (!config.caps.perDay || !config.caps.perMonth) {
    log.warn("STT_MAX_SECONDS_PER_DAY·_MONTH 가 비어 있다 — /ingest 는 거절한다(COST-1)");
  }
});

// 쿠버네티스가 파드를 내릴 때 SIGTERM 을 준다. 쌓인 사용량을 장부에 쓰고 내려간다.
for (const signal of ["SIGTERM", "SIGINT"] as const) {
  process.on(signal, () => {
    log.info(`${signal} — 사용량을 장부에 쓰고 내려간다`);
    server.close();
    void budget.flush().finally(() => process.exit(0));
  });
}
