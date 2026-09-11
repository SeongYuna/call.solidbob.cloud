// Requirement: A-1, A-2, A-3, SEC-1
/**
 * 게이트웨이의 바깥 표면. 포트 하나에 셋이 있다.
 *
 * | 경로 | 누가 | 무엇이 흐르나 |
 * |---|---|---|
 * | `WS /ingest?call_id=&speaker=&sample_rate=&channels=` | 오디오 생산자 | → PCM16LE 모노 바이너리 |
 * | `WS /ws[?call_id=]` (별칭 `/dashboard`) | 대시보드 | ← `{type, payload}` JSON (마스킹된 결과만) |
 * | `GET /dev` · `WS /dev/text?call_id=&speaker=` | 개발자 브라우저 | → 브라우저 음성 인식 결과 글자(`decisions/109`) |
 * | `GET /health` | 쿠버네티스·사람 | ← 설정 여부·사용량 (값·주소는 싣지 않는다, SEC-2) |
 *
 * **운영에서는 `https://server.solidbob.cloud/gateway/…` 로 열린다**(Ingress 경로 `/gateway`). 밖에 여는 주소가
 * 그 도메인 하나라서다(런북 16-2·18). 접두어는 여기서 떼므로 `/gateway/ws` 와 `/ws` 가 같다 — Traefik
 * 미들웨어(CRD)에 기대지 않으려는 것이다.
 *
 * 생산자는 지금은 `scripts/stream_wav.ts`(AI Hub 녹음 재생)다. 브라우저 마이크 캡처는
 * `apps/dashboard` 몫이고, 같은 `/ingest` 계약으로 붙는다.
 *
 * 대시보드 쪽은 **받기만 한다** — `realGatewayClient.ts` 가 보내는 메시지가 없다. `call_id` 를
 * 안 주면 모든 통화를 받는다(상담원 한 명 데모). 형식은 그 파서가 이미 기다리는 것 그대로다.
 *
 * 접속은 두 겹으로 거른다.
 * ① **토큰** (`domain/access.ts`) — 이 머신 밖에서 오면 **문마다 다른** 토큰이 맞아야 한다.
 *    `/ingest`·`/dev/text`(둘 다 DB 에 전사를 쓴다)는 `GATEWAY_INGEST_TOKEN` 을 `Authorization: Bearer` 나
 *    서브프로토콜 `bearer.<토큰>` 으로만 — URL 에 비밀을 싣지 않는다. 브라우저(`/dev`)는 서브프로토콜로 낸다.
 *    프록시 헤더가 붙은 루프백 요청은 «이 머신» 으로 치지 않는다(ngrok 같은 터널).
 *    `/ws` 는 `GATEWAY_VIEW_TOKEN` 을 헤더나 `?token=` 으로(브라우저 WebSocket 은 헤더를 못 붙인다).
 *    `/health` 는 거르지 않는다(쿠버네티스 프로브가 토큰 없이 부른다 — 자막·과금과 무관한 숫자만 싣는다).
 * ② **`Origin`** — 있으면 허용 목록과 대조한다. 토큰을 가진 페이지라도 남의 사이트면 막는다.
 */
import { createServer, type IncomingMessage, type Server, type ServerResponse } from "node:http";
import type { Duplex } from "node:stream";
import { WebSocketServer, type WebSocket, type RawData } from "ws";
import type { CallRegistry, Channel } from "../app/call_registry.ts";
import {
  bearerFromSubprotocols,
  bearerToken,
  decideAccess,
  forwardedByProxy,
  isLoopback,
  SUBPROTOCOL,
} from "../domain/access.ts";
import { DEV_PAGE_HEADERS, DEV_PAGE_HTML } from "./dev_page.ts";
import type { Broadcaster, GatewayMessage, Logger, Speaker } from "../app/ports.ts";

// ── 대시보드 구독 ────────────────────────────────────────────────────────────

export class DashboardHub implements Broadcaster {
  private readonly subscribers = new Map<WebSocket, string | null>();

  add(socket: WebSocket, callId: string | null): void {
    this.subscribers.set(socket, callId);
    socket.on("close", () => this.subscribers.delete(socket));
  }

  get size(): number {
    return this.subscribers.size;
  }

  publish(callId: string, message: GatewayMessage): void {
    const text = JSON.stringify(message);
    for (const [socket, filter] of this.subscribers) {
      if ((filter === null || filter === callId) && socket.readyState === socket.OPEN) {
        socket.send(text);
      }
    }
  }
}

// ── 서버 ─────────────────────────────────────────────────────────────────────

export interface GatewayServerDeps {
  registry: CallRegistry;
  dashboards: DashboardHub;
  allowedOrigins: readonly string[];
  /** 문마다 토큰. 빈 문자열이면 설정되지 않았다 — 믿는 주소 밖은 전부 거절한다. */
  tokens: { ingest: string; view: string };
  /** 토큰 없이 받을 주소인가. 기본은 루프백. 테스트가 «바깥 클라이언트» 를 흉내 낼 때 바꾼다. */
  isTrustedAddress?: (address: string | undefined) => boolean;
  /** 연결 유지 ping 간격(ms). 테스트가 줄인다. */
  heartbeatMs?: number;
  health: () => Record<string, unknown>;
  log: Logger;
}

/** 표준 close 코드. 1008 = 규칙 위반(잘못된 요청), 1013 = 나중에 다시(한도), 1011 = 서버 쪽 문제. */
const CLOSE_POLICY = 1008;
const CLOSE_TRY_LATER = 1013;
const CLOSE_INTERNAL = 1011;
const CLOSE_NORMAL = 1000;

const CALL_ID = /^[A-Za-z0-9_.:-]{1,40}$/;

/**
 * 경로 → 문. `audio`·`text` 는 전사를 DB 에 쓰므로 과금 문 토큰(`ingest`)을, `view` 는 대시보드 토큰을 쓴다.
 * `/dashboard` 는 조서희 님 게이트웨이(frontend 브랜치, `decisions/402`)가 쓰던 대시보드 경로다 — 그쪽 안내대로
 * 붙인 대시보드가 그대로 붙게 별칭으로 받는다(`decisions/109`).
 */
const ROUTES: Record<string, "audio" | "text" | "view"> = {
  "/ingest": "audio",
  "/dev/text": "text",
  "/ws": "view",
  "/dashboard": "view",
};

/** 글자 한 건 상한. 브라우저 인식 결과 한 문장은 수백 자를 넘지 않는다 — 넘으면 잘못된 입력이다. */
const MAX_TEXT_CHARS = 2000;

/** 운영 Ingress 가 붙이는 경로. `ingress.yaml` 의 `/gateway` 와 같아야 한다. */
export const PUBLIC_PREFIX = "/gateway";

/** 연결 유지 ping 간격. 프록시(Traefik)는 오래 조용한 연결을 끊는다 — 대기 중인 대시보드가 그렇다. */
const HEARTBEAT_MS = 25_000;

/** `/gateway/ws` → `/ws`. 접두어가 없으면 그대로. */
export function routePath(pathname: string): string {
  if (pathname === PUBLIC_PREFIX) {
    return "/";
  }
  return pathname.startsWith(`${PUBLIC_PREFIX}/`) ? pathname.slice(PUBLIC_PREFIX.length) : pathname;
}
const SAMPLE_RATES = new Set([8000, 16000, 22050, 24000, 44100, 48000]);

export function createGatewayServer(deps: GatewayServerDeps): Server {
  // 브라우저가 서브프로토콜로 토큰을 내면 `callguard` 를 골라 되돌려 준다 — 토큰 항목은 절대 되돌리지 않는다.
  const handleProtocols = (protocols: Set<string>): string | false => (protocols.has(SUBPROTOCOL) ? SUBPROTOCOL : false);
  const ingestWss = new WebSocketServer({ noServer: true, maxPayload: 1 << 20, handleProtocols });
  const textWss = new WebSocketServer({ noServer: true, maxPayload: 16 << 10, handleProtocols });
  const dashboardWss = new WebSocketServer({ noServer: true, handleProtocols });

  const server = createServer((req, res) => handleHttp(req, res, deps));

  // 연결 유지 — ping 을 보내고, 다음 차례까지 pong 이 없으면 죽은 연결로 보고 끊는다.
  const alive = new WeakMap<WebSocket, boolean>();
  const track = (ws: WebSocket): void => {
    alive.set(ws, true);
    ws.on("pong", () => alive.set(ws, true));
  };
  const heartbeat = setInterval(() => {
    for (const wss of [ingestWss, textWss, dashboardWss]) {
      for (const ws of wss.clients) {
        if (alive.get(ws) === false) {
          ws.terminate();
          continue;
        }
        alive.set(ws, false);
        ws.ping();
      }
    }
  }, deps.heartbeatMs ?? HEARTBEAT_MS);
  heartbeat.unref();
  server.on("close", () => clearInterval(heartbeat));

  server.on("upgrade", (req: IncomingMessage, socket: Duplex, head: Buffer) => {
    const url = new URL(req.url ?? "/", "http://gateway.local");
    const path = routePath(url.pathname);
    const origin = req.headers.origin;
    if (origin !== undefined && !deps.allowedOrigins.includes(origin)) {
      socket.end("HTTP/1.1 403 Forbidden\r\n\r\n");
      return;
    }
    const route = ROUTES[path];
    if (route === undefined) {
      socket.end("HTTP/1.1 404 Not Found\r\n\r\n");
      return;
    }
    const door = route === "view" ? "view" : "ingest";
    const trusted =
      (deps.isTrustedAddress ?? isLoopback)(req.socket.remoteAddress) && !forwardedByProxy(req.headers);
    const header = bearerToken(req.headers.authorization) ?? bearerFromSubprotocols(req.headers["sec-websocket-protocol"]);
    // 전사를 쓰는 문의 비밀은 헤더(또는 서브프로토콜)로만 받는다. 대시보드 토큰은 비밀이 아니라 URL 도 받는다.
    const presented = door === "ingest" ? header : (header ?? url.searchParams.get("token"));
    const access = decideAccess(deps.tokens[door], presented, trusted);
    if (!access.ok) {
      // 토큰·주소·쿼리는 로그에 남기지 않는다. 어느 문으로 왔고 왜 막혔는지만.
      deps.log.warn(`접속 거절 ${path} — ${access.reason}`);
      socket.end("HTTP/1.1 401 Unauthorized\r\n\r\n");
      return;
    }
    if (route === "audio") {
      ingestWss.handleUpgrade(req, socket, head, (ws) => {
        track(ws);
        void acceptIngest(ws, url, deps);
      });
      return;
    }
    if (route === "text") {
      textWss.handleUpgrade(req, socket, head, (ws) => {
        track(ws);
        void acceptText(ws, url, deps);
      });
      return;
    }
    dashboardWss.handleUpgrade(req, socket, head, (ws) => {
      track(ws);
      deps.dashboards.add(ws, url.searchParams.get("call_id"));
      ws.on("message", () => {}); // 대시보드는 보내는 메시지가 없다. 와도 무시한다.
    });
  });

  return server;
}

function handleHttp(req: IncomingMessage, res: ServerResponse, deps: GatewayServerDeps): void {
  const url = new URL(req.url ?? "/", "http://gateway.local");
  if (req.method === "GET" && routePath(url.pathname) === "/health") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify(deps.health()));
    return;
  }
  if (req.method === "GET" && routePath(url.pathname) === "/dev") {
    // 페이지에는 비밀이 없다 — 토큰은 개발자가 붙여 넣는다. 헤더는 dev_page.ts(CSP·틀 금지·캐시 금지).
    res.writeHead(200, DEV_PAGE_HEADERS);
    res.end(DEV_PAGE_HTML);
    return;
  }
  res.writeHead(404, { "content-type": "application/json" });
  res.end(JSON.stringify({ detail: "Not Found" }));
}

interface IngestParams {
  callId: string;
  speaker: Speaker;
  sampleRate: number;
  channelCount: number;
}

function parseIngest(url: URL): IngestParams | string {
  const callId = url.searchParams.get("call_id") ?? "";
  if (!CALL_ID.test(callId)) {
    return "call_id 는 영문·숫자·_.:- 1~40자다";
  }
  const speaker = url.searchParams.get("speaker");
  if (speaker !== "agent" && speaker !== "customer") {
    return "speaker 는 agent 또는 customer 다";
  }
  const sampleRate = Number(url.searchParams.get("sample_rate") ?? "16000");
  if (!SAMPLE_RATES.has(sampleRate)) {
    return `sample_rate 는 ${[...SAMPLE_RATES].join("·")} 중 하나다`;
  }
  const channelCount = Number(url.searchParams.get("channels") ?? "1");
  if (channelCount !== 1 && channelCount !== 2) {
    return "channels 는 1 또는 2 다";
  }
  return { callId, speaker, sampleRate, channelCount };
}

async function acceptIngest(ws: WebSocket, url: URL, deps: GatewayServerDeps): Promise<void> {
  const params = parseIngest(url);
  if (typeof params === "string") {
    closeWith(ws, CLOSE_POLICY, params);
    return;
  }

  // 채널이 열리는 동안(통화 시작 요청) 도착한 오디오는 모아 뒀다가 연 뒤에 흘린다.
  const early: Buffer[] = [];
  let channel: Channel | null = null;
  let producerDone = false;

  ws.on("message", (data: RawData, isBinary: boolean) => {
    if (!isBinary) {
      if (isEndMessage(data)) {
        producerDone = true;
        if (channel !== null) {
          void channel.close().then(() => closeWith(ws, CLOSE_NORMAL, "끝"));
        }
      }
      return;
    }
    const pcm = toBuffer(data);
    if (channel === null) {
      early.push(pcm);
      return;
    }
    channel.pushAudio(pcm);
  });
  ws.on("close", () => {
    producerDone = true;
    void channel?.close();
  });

  const result = await deps.registry.open({
    callId: params.callId,
    speaker: params.speaker,
    sampleRate: params.sampleRate,
    channelCount: params.channelCount,
  });
  if (!result.ok) {
    deps.log.warn(`채널 거절 call=${params.callId} speaker=${params.speaker} — ${result.reason}`);
    closeWith(ws, result.kind === "budget" ? CLOSE_TRY_LATER : result.kind === "busy" ? CLOSE_POLICY : CLOSE_INTERNAL, result.reason);
    return;
  }
  channel = result.channel;
  deps.log.info(`채널 열림 call=${params.callId} speaker=${params.speaker} rate=${params.sampleRate}`);
  channel.onStop((reason) => closeWith(ws, reason.includes("한도") ? CLOSE_TRY_LATER : CLOSE_INTERNAL, reason));

  for (const pcm of early.splice(0)) {
    if (!channel.pushAudio(pcm)) {
      break;
    }
  }
  if (producerDone) {
    await channel.close();
    closeWith(ws, CLOSE_NORMAL, "끝");
  }
}

/**
 * `WS /dev/text` — 브라우저 음성 인식이 이미 글자로 바꾼 결과를 받는다(`decisions/109`).
 * 메시지: `{"text": "...", "is_final": true|false}` · 끝낼 때 `{"type":"end"}`. 바이너리는 받지 않는다.
 */
async function acceptText(ws: WebSocket, url: URL, deps: GatewayServerDeps): Promise<void> {
  const params = parseIngest(url);
  if (typeof params === "string") {
    closeWith(ws, CLOSE_POLICY, params);
    return;
  }
  const early: Array<{ text: string; isFinal: boolean }> = [];
  let channel: Channel | null = null;
  let producerDone = false;

  ws.on("message", (data: RawData, isBinary: boolean) => {
    if (isBinary) {
      closeWith(ws, CLOSE_POLICY, "이 문은 글자만 받는다 — 오디오는 /ingest");
      return;
    }
    if (isEndMessage(data)) {
      producerDone = true;
      if (channel !== null) {
        void channel.close().then(() => closeWith(ws, CLOSE_NORMAL, "끝"));
      }
      return;
    }
    const item = parseTextMessage(data);
    if (item === null) {
      closeWith(ws, CLOSE_POLICY, `메시지는 {"text": 글자(${MAX_TEXT_CHARS}자 이하), "is_final": 참거짓} 이다`);
      return;
    }
    if (channel === null) {
      early.push(item);
      return;
    }
    channel.pushText(item.text, item.isFinal);
  });
  ws.on("close", () => {
    producerDone = true;
    void channel?.close();
  });

  const result = await deps.registry.open({
    callId: params.callId,
    speaker: params.speaker,
    sampleRate: params.sampleRate,
    channelCount: params.channelCount,
    source: "text",
  });
  if (!result.ok) {
    deps.log.warn(`글자 채널 거절 call=${params.callId} speaker=${params.speaker} — ${result.reason}`);
    closeWith(ws, result.kind === "busy" ? CLOSE_POLICY : CLOSE_INTERNAL, result.reason);
    return;
  }
  channel = result.channel;
  deps.log.info(`글자 채널 열림 call=${params.callId} speaker=${params.speaker} (web-speech)`);
  for (const item of early.splice(0)) {
    channel.pushText(item.text, item.isFinal);
  }
  if (producerDone) {
    await channel.close();
    closeWith(ws, CLOSE_NORMAL, "끝");
  }
}

function parseTextMessage(data: RawData): { text: string; isFinal: boolean } | null {
  try {
    const parsed: unknown = JSON.parse(toBuffer(data).toString("utf-8"));
    if (typeof parsed !== "object" || parsed === null) {
      return null;
    }
    const { text, is_final: isFinal } = parsed as { text?: unknown; is_final?: unknown };
    if (typeof text !== "string" || text.length > MAX_TEXT_CHARS || typeof isFinal !== "boolean") {
      return null;
    }
    return { text, isFinal };
  } catch {
    return null;
  }
}

function isEndMessage(data: RawData): boolean {
  try {
    const parsed: unknown = JSON.parse(toBuffer(data).toString("utf-8"));
    return typeof parsed === "object" && parsed !== null && (parsed as { type?: unknown }).type === "end";
  } catch {
    return false;
  }
}

function toBuffer(data: RawData): Buffer {
  if (Buffer.isBuffer(data)) {
    return data;
  }
  if (Array.isArray(data)) {
    return Buffer.concat(data);
  }
  return Buffer.from(data);
}

/** close reason 은 123바이트가 한도다. 한글은 3바이트라 글자 수가 아니라 바이트로 자른다. */
function closeWith(ws: WebSocket, code: number, reason: string): void {
  if (ws.readyState === ws.CLOSED || ws.readyState === ws.CLOSING) {
    return;
  }
  let bytes = Buffer.from(reason, "utf-8");
  if (bytes.byteLength > 123) {
    let cut = 123;
    while (cut > 0 && ((bytes[cut] ?? 0) & 0xc0) === 0x80) {
      cut -= 1; // UTF-8 이어지는 바이트 한가운데서 자르지 않는다
    }
    bytes = bytes.subarray(0, cut);
  }
  ws.close(code, bytes.toString("utf-8"));
}
