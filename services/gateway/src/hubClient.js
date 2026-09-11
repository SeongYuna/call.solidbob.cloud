// Requirement: A-1, A-2, C-5
// server/apps/hub 호출. 마스킹(C-5)은 이미 POST /hub/transcripts 안에 있어서
// 게이트웨이가 따로 마스킹 로직을 만들지 않는다 — 절대 원칙: 마스킹 없는
// 임시 통과 경로를 만들지 않는다. 이 호출이 실패하면 그 구간은 대시보드로
// 보내지 않는다(마스킹을 거치지 않은 원문을 내보내지 않기 위해).
const HUB_API_URL = (process.env.HUB_API_URL ?? "").replace(/\/+$/, "");

function assertConfigured() {
  if (HUB_API_URL.length === 0) {
    throw new Error("HUB_API_URL이 설정되지 않았습니다 (.env 확인).");
  }
}

export async function createCall(callId, sttEngine = "google") {
  assertConfigured();
  const res = await fetch(`${HUB_API_URL}/hub/calls`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "1",
    },
    body: JSON.stringify({ call_id: callId, stt_engine: sttEngine }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`POST /hub/calls 실패 (${res.status}): ${body}`);
  }
  return res.json();
}

/**
 * 전사 한 구간을 hub로 보내 마스킹된 결과를 받는다. 응답은 이미 대시보드
 * 파서(realGatewayClient.ts)가 기대하는 모양 그대로다 — 그대로 중계한다.
 */
export async function ingestTranscript({
  callId,
  segmentId,
  speaker,
  text,
  isFinal,
  utteranceEndMs,
}) {
  assertConfigured();
  const res = await fetch(`${HUB_API_URL}/hub/transcripts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "ngrok-skip-browser-warning": "1",
    },
    body: JSON.stringify({
      call_id: callId,
      segment_id: segmentId,
      speaker,
      text,
      is_final: isFinal,
      utterance_end_ms: utteranceEndMs,
    }),
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`POST /hub/transcripts 실패 (${res.status}): ${body}`);
  }
  return res.json();
}
