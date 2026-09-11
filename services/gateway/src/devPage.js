// Requirement: A-1, A-2
// 전화 사업자(Twilio 등) 없이, 그리고 Google Cloud STT 자격증명(류준·장민석
// 몫 — server/CLAUDE.md·infra-runbook 이 전제하는 GCP 프로젝트) 없이도,
// 개발자 본인 폰 브라우저만으로 "통화"를 흉내 내는 테스트 페이지.
//
// 브라우저 내장 Web Speech API(SpeechRecognition)로 그 자리에서 바로
// 텍스트로 바꿔 보낸다 — 오디오를 서버로 보내지 않으므로 서버 쪽
// googleStt.js(A-1/A-2 본체, Twilio 경로용)를 전혀 타지 않고, COST-1 사용량
// 가드도 걸리지 않는다(과금 대상 API 호출 자체가 없다). 대신 STT 품질은
// 브라우저 엔진 그대로다 — 정식 파이프라인 품질 측정용이 아니라 "게이트웨이
// →hub→대시보드 배선이 실제로 도는지"를 개인적으로 확인하는 용도다.
//
// 프로토콜 (server.js devWss 와 1:1 대응):
//   클라이언트 "start"     → 텍스트 JSON { event: "start" }
//   클라이언트 인식 결과   → 텍스트 JSON { event: "asr-text", text, isFinal }
//   클라이언트 "stop"      → 텍스트 JSON { event: "stop" }
// 마이크 권한은 HTTPS(또는 localhost)에서만 열리므로, 폰에서 열려면 ngrok
// 같은 HTTPS 터널이 필요하다.
export const DEV_PAGE_HTML = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>CallGuard 게이트웨이 개발용 테스트 콜</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 480px; margin: 24px auto; padding: 0 16px; }
  button { font-size: 18px; padding: 14px 20px; width: 100%; border-radius: 10px; border: none; }
  #start { background: #16a34a; color: white; }
  #stop { background: #dc2626; color: white; }
  #stop[disabled], #start[disabled] { opacity: 0.4; }
  #status { margin: 12px 0; font-size: 14px; color: #555; white-space: pre-wrap; }
  #log { font-size: 12px; color: #888; height: 200px; overflow-y: auto; border: 1px solid #ddd; padding: 8px; border-radius: 6px; }
</style>
</head>
<body>
  <h2>게이트웨이 테스트 콜</h2>
  <p style="font-size:12px;color:#888;">전화 사업자·Google STT 자격증명 없음 — 브라우저 음성 인식만 사용</p>
  <p id="status">대기 중</p>
  <button id="start">통화 시작</button>
  <button id="stop" disabled>통화 종료</button>
  <div id="log"></div>
<script>
(function () {
  const startBtn = document.getElementById("start");
  const stopBtn = document.getElementById("stop");
  const statusEl = document.getElementById("status");
  const logEl = document.getElementById("log");

  function log(line) {
    const p = document.createElement("div");
    p.textContent = "[" + new Date().toLocaleTimeString() + "] " + line;
    logEl.prepend(p);
  }

  const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;

  let ws = null;
  let recognition = null;
  let calling = false;

  function sendJson(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(obj));
    }
  }

  function startRecognition() {
    recognition = new SpeechRecognitionImpl();
    recognition.lang = "ko-KR";
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript;
        const isFinal = result.isFinal === true;
        sendJson({ event: "asr-text", text, isFinal });
        log((isFinal ? "[최종] " : "[중간] ") + text);
      }
    };

    recognition.onerror = (event) => {
      log("인식 오류: " + event.error);
    };

    // continuous 모드도 브라우저가 무음 등으로 가끔 스스로 끝낸다 —
    // 통화 중이면(calling) 즉시 재시작해 끊김 없이 이어간다.
    recognition.onend = () => {
      if (calling) {
        try {
          recognition.start();
        } catch {
          // 이미 시작된 상태에서 start() 를 다시 부르면 던진다 — 무시해도 된다.
        }
      }
    };

    recognition.start();
  }

  startBtn.addEventListener("click", async () => {
    if (!window.isSecureContext) {
      statusEl.textContent = "HTTPS(또는 localhost)가 아니면 마이크를 열 수 없습니다. ngrok 등으로 접속하세요.";
      return;
    }
    if (!SpeechRecognitionImpl) {
      statusEl.textContent = "이 브라우저는 음성 인식을 지원하지 않습니다 (Chrome 권장).";
      return;
    }

    startBtn.disabled = true;
    statusEl.textContent = "연결 중...";

    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(proto + "//" + location.host + "/dev/media");

    ws.addEventListener("open", () => {
      statusEl.textContent = "연결됨 — 통화 시작 신호 전송";
      sendJson({ event: "start" });
      stopBtn.disabled = false;
      calling = true;
      startRecognition();
      statusEl.textContent = "통화 중 — 말씀하세요";
      log("통화 시작");
    });

    ws.addEventListener("message", (event) => {
      log(event.data);
    });

    ws.addEventListener("close", () => {
      log("연결 종료");
      startBtn.disabled = false;
      stopBtn.disabled = true;
      if (statusEl.textContent === "통화 중 — 말씀하세요") {
        statusEl.textContent = "연결이 끊어졌습니다";
      }
    });

    ws.addEventListener("error", () => {
      log("WebSocket 오류");
    });
  });

  function stopCall() {
    calling = false;
    try {
      recognition?.stop();
    } catch {
      // ignore
    }
    sendJson({ event: "stop" });
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
    startBtn.disabled = false;
    stopBtn.disabled = true;
    statusEl.textContent = "통화 종료됨";
  }

  stopBtn.addEventListener("click", stopCall);
})();
</script>
</body>
</html>
`;
