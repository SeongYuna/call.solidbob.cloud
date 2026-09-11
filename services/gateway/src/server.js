// Requirement: A-3
// 대시보드 실시간 자막 배선: /dev(브라우저 음성인식) → hub(마스킹) →
// apps/dashboard(WebSocket). server/CLAUDE.md·rfp-harness.md가 원래 예정해
// 둔 services/gateway 자리를 처음 채운다.
//
// ⚠ 담당 경계 — `_project/decisions/012`(디렉터리 경계 = 담당 경계)상
// services/gateway는 정성윤 담당이다. 사용자 지시로 조서희가 만들었다
// (2026-09-10) — decisions/023이 이미 정한 대로 협의를 절차로 요구하지
// 않지만, 경계를 넘었다는 사실은 세션 기록에 남긴다.
//
// ⚠ 실제 전화망(Twilio 등) 연동은 이 파일에 없다(2026-09-11, 사용자 지시로
// 제거). 그 경로는 Google Cloud STT 서비스 계정 키가 있어야 했는데, 지금은
// 전화 사업자 계정 자체를 안 쓰기로 했다 — A-1/A-2 본체(실제 전화 연동)는
// 여전히 팀의 미완료 항목이고, 누가 언제 어떤 사업자로 다시 붙일지는
// 정해지지 않았다.
import "dotenv/config";
import express from "express";
import { WebSocketServer } from "ws";
import { createServer } from "node:http";
import { createCall, ingestTranscript } from "./hubClient.js";
import { broadcastToDashboard, registerDashboardClient } from "./dashboardHub.js";
import { DEV_PAGE_HTML } from "./devPage.js";

const PORT = Number(process.env.GATEWAY_PORT ?? 8080);
const CALL_ID_PREFIX = process.env.HUB_CALL_ID_PREFIX ?? "test-";

/**
 * 통화 하나(/dev 브라우저 테스트)의 텍스트→hub→대시보드 배선을 만든다.
 * 텍스트는 이미 브라우저 Web Speech API가 만들어 온 것을 pushText() 로
 * 받는다 — 여기서 오디오를 다루거나 STT 를 직접 호출하지 않는다.
 */
function createCallSession() {
  const call = {
    callId: "",
    startedAt: 0,
    nextSegmentId: 1,
    currentSegmentId: null,
  };
  // stop() 은 명시적 "stop" 메시지와 ws close 양쪽에서 불릴 수 있다 —
  // 두 번째 호출은 아무 일도 하지 않게 막는다.
  let stopped = false;

  function handleSttResult({ text, isFinal }) {
    if (text.trim().length === 0) {
      return;
    }
    if (call.currentSegmentId === null) {
      call.currentSegmentId = call.nextSegmentId;
    }
    const segmentId = call.currentSegmentId;
    const utteranceEndMs = Date.now() - call.startedAt;

    ingestTranscript({
      callId: call.callId,
      segmentId,
      speaker: "customer",
      text,
      isFinal,
      utteranceEndMs,
    })
      .then((masked) => {
        // hub 응답이 이미 대시보드 파서가 기대하는 모양이라 그대로 중계한다.
        broadcastToDashboard(masked);
      })
      .catch((error) => {
        // ⚠ 마스킹 호출이 실패하면 이 구간은 대시보드로 보내지 않는다 —
        // 마스킹 없는 원문을 내보내지 않기 위해서다(절대 원칙, C-5).
        console.error("[gateway] hub 마스킹 호출 실패, 이 구간은 건너뜁니다:", error.message);
      });

    if (isFinal) {
      call.nextSegmentId += 1;
      call.currentSegmentId = null;
    }
  }

  return {
    start(callId) {
      call.callId = callId;
      call.startedAt = Date.now();
      console.log(`[gateway] 통화 시작 ${call.callId}`);

      createCall(call.callId, "browser").catch((error) => {
        console.error("[gateway] POST /hub/calls 실패:", error.message);
      });
    },
    /** 브라우저가 이미 인식한 텍스트를 그대로 밀어넣는다. */
    pushText({ text, isFinal }) {
      handleSttResult({ text, isFinal });
    },
    stop() {
      if (stopped) {
        return;
      }
      stopped = true;
      console.log(`[gateway] 통화 종료 ${call.callId}`);
    },
  };
}

const app = express();
app.use(express.urlencoded({ extended: false }));

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

/**
 * 전화 사업자·STT 자격증명 없이 개발자 본인 폰(또는 컴퓨터) 브라우저만으로
 * "통화"를 흉내 내는 테스트 페이지. HTTPS(또는 localhost)에서만 마이크가
 * 열리므로, 폰에서 쓰려면 ngrok 같은 HTTPS 터널이 필요하다.
 */
app.get("/dev", (_req, res) => {
  res.type("html").send(DEV_PAGE_HTML);
});

const server = createServer(app);

const devWss = new WebSocketServer({ noServer: true });
const dashboardWss = new WebSocketServer({ noServer: true });

server.on("upgrade", (req, socket, head) => {
  if (req.url === "/dev/media") {
    devWss.handleUpgrade(req, socket, head, (ws) => {
      devWss.emit("connection", ws, req);
    });
  } else if (req.url === "/dashboard") {
    dashboardWss.handleUpgrade(req, socket, head, (ws) => {
      dashboardWss.emit("connection", ws, req);
    });
  } else {
    socket.destroy();
  }
});

dashboardWss.on("connection", (ws) => {
  registerDashboardClient(ws);
});

/**
 * /dev 페이지가 붙는 쪽. 전부 텍스트 JSON 프레임이다 — 오디오 자체는
 * 서버로 오지 않는다(devPage.js가 브라우저 Web Speech API로 이미 텍스트로
 * 바꿔서 보낸다).
 *   { event: "start" }
 *   { event: "asr-text", text, isFinal }
 *   { event: "stop" }
 */
let devCallSeq = 0;

devWss.on("connection", (ws) => {
  let session = null;

  ws.on("message", (raw) => {
    let msg;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }

    if (msg.event === "start") {
      devCallSeq += 1;
      session = createCallSession();
      session.start(`${CALL_ID_PREFIX}dev-mic-${Date.now()}-${devCallSeq}`);
      return;
    }

    if (msg.event === "asr-text") {
      session?.pushText({ text: String(msg.text ?? ""), isFinal: msg.isFinal === true });
      return;
    }

    if (msg.event === "stop") {
      session?.stop();
    }
  });

  ws.on("close", () => {
    session?.stop();
  });
});

server.listen(PORT, () => {
  console.log(`[gateway] 포트 ${PORT}에서 대기 중`);
  console.log(`[gateway] 개발용 테스트 콜: GET /dev`);
  console.log(`[gateway] 대시보드 접속용: GET /dashboard (WebSocket)`);
});
