export function coreApiUrl(): string {
  return (import.meta.env.VITE_CORE_API_URL ?? "").trim();
}

export function isCoreApiConfigured(): boolean {
  return coreApiUrl().length > 0;
}

/**
 * GET /hub/calls 목록 API 연결 전 임시 mock.
 * 실제 엔드포인트가 생기면 여기서 REST 로 바꾼다.
 */
export { listCallHistory, getCallTranscript, getHistoryPlayback } from "../../mock/callHistory";
