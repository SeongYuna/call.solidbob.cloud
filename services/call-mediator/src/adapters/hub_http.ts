// Requirement: 7.3절, SEC-1
/**
 * server(FastAPI 허브)를 HTTP 로 부른다. 운영에서는 같은 네임스페이스의 Service 이름
 * (`http://callguard-server`)이고, 로컬에서는 `http://localhost:8000` 이다.
 *
 * 실패는 상태 코드만 담은 `HubError` 로 올린다 — 응답 본문을 에러 메시지에 싣지 않는다.
 * 서버의 422 본문은 요청값(원문 전사)을 그대로 되돌려 주기 때문이다(pydantic `input`).
 */
import {
  HubError,
  type CallStartRequest,
  type CallGuardCheckRequest,
  type CallGuardPayload,
  type ClosurePayload,
  type ComplianceCheckRequest,
  type CompliancePayload,
  type RequiredDocsCheckRequest,
  type HubPort,
  type MaskedTranscript,
  type RawTranscript,
  type RecommendPayload,
  type RecommendRequest,
  type RoutingDecisionPayload,
  type RoutingDecisionRequest,
  type CallStartResult,
} from "../app/ports.ts";

export class HttpHub implements HubPort {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly headers: Record<string, string>;

  /**
   * `serviceToken` — server 쓰기 경로의 문(`INGEST_SERVICE_TOKEN`, `_project/decisions/120`).
   * 2026-09-20 운영 왕복에서 이 경로들이 **토큰 없이 200** 이었다. 비어 있으면 헤더를 보내지 않는다 —
   * server 가 아직 토큰을 요구하지 않는 이행기에도 같은 코드로 돈다. **값은 어디에도 로깅하지 않는다**(SEC-2).
   */
  constructor(baseUrl: string, timeoutMs = 5_000, serviceToken = "") {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.timeoutMs = timeoutMs;
    this.headers = { "content-type": "application/json" };
    if (serviceToken.length > 0) {
      this.headers.authorization = `Bearer ${serviceToken}`;
    }
  }

  async startCall(request: CallStartRequest): Promise<CallStartResult> {
    const body = await this.post("/hub/calls", request);
    return { lastSegmentId: lastSegmentIdOf(body) };
  }

  async decideRouting(request: RoutingDecisionRequest): Promise<RoutingDecisionPayload> {
    const body = await this.post("/hub/routing-decisions", request);
    if (typeof body !== "object" || body === null) {
      throw new HubError("배정 판정 응답 형식이 계약과 다르다", null);
    }
    return body as RoutingDecisionPayload;
  }

  async ingestTranscript(raw: RawTranscript): Promise<MaskedTranscript> {
    const body = await this.post("/hub/transcripts", raw);
    if (typeof body !== "object" || body === null || typeof (body as { text?: unknown }).text !== "string") {
      throw new HubError("전사 응답 형식이 계약과 다르다", null);
    }
    return body as MaskedTranscript;
  }

  async recommend(request: RecommendRequest): Promise<RecommendPayload> {
    const body = await this.post("/hub/recommendations", request);
    if (typeof body !== "object" || body === null) {
      throw new HubError("추천 응답 형식이 계약과 다르다", null);
    }
    return body as RecommendPayload;
  }

  async checkCallGuard(request: CallGuardCheckRequest): Promise<CallGuardPayload> {
    const body = await this.post("/hub/call-guard-checks", request);
    if (typeof body !== "object" || body === null || !Array.isArray((body as { flags?: unknown }).flags)) {
      throw new HubError("콜 가드 응답 형식이 계약과 다르다", null);
    }
    return body as CallGuardPayload;
  }

  async checkCompliance(request: ComplianceCheckRequest): Promise<CompliancePayload> {
    const body = await this.post("/hub/compliance-checks", request);
    if (typeof body !== "object" || body === null || !Array.isArray((body as { findings?: unknown }).findings)) {
      throw new HubError("컴플라이언스 응답 형식이 계약과 다르다", null);
    }
    return body as CompliancePayload;
  }

  async checkRequiredDocs(request: RequiredDocsCheckRequest): Promise<ClosurePayload> {
    const body = await this.post("/hub/required-docs-checks", request);
    if (typeof body !== "object" || body === null || typeof (body as { procedure?: unknown }).procedure !== "string") {
      throw new HubError("필요서류 판정 응답 형식이 계약과 다르다", null);
    }
    return body as ClosurePayload;
  }

  private async post(path: string, payload: unknown): Promise<unknown> {
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: this.headers,
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(this.timeoutMs),
      });
    } catch {
      throw new HubError(`${path} 연결 실패`, null);
    }
    if (!response.ok) {
      // 본문을 읽어 버리기만 한다 — 422 본문에는 원문이 들어 있다.
      await response.arrayBuffer().catch(() => undefined);
      throw new HubError(`${path} ${response.status}`, response.status);
    }
    return response.json();
  }
}

/**
 * 응답의 `last_segment_id`(서버는 숫자를 문자열로 싣는다 — `StrField`). 없거나 이상하면 0 — 옛 서버와도 돈다.
 * 0 이면 지금처럼 1부터 센다.
 */
export function lastSegmentIdOf(body: unknown): number {
  if (typeof body !== "object" || body === null) {
    return 0;
  }
  const raw = (body as { last_segment_id?: unknown }).last_segment_id;
  const value = typeof raw === "string" ? Number(raw) : raw;
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0 ? value : 0;
}
