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
  type HubPort,
  type MaskedTranscript,
  type RawTranscript,
  type RecommendPayload,
  type RecommendRequest,
} from "../app/ports.ts";

export class HttpHub implements HubPort {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(baseUrl: string, timeoutMs = 5_000) {
    this.baseUrl = baseUrl.replace(/\/+$/, "");
    this.timeoutMs = timeoutMs;
  }

  async startCall(request: CallStartRequest): Promise<void> {
    await this.post("/hub/calls", request);
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

  private async post(path: string, payload: unknown): Promise<unknown> {
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
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
