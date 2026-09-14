// Requirement: A-3
/**
 * `GET /dev` — 폰·PC 브라우저만으로 통화를 흉내 내는 개발용 페이지. 조서희 님이 frontend 브랜치에서
 * 만든 경로(`decisions/402`)를 정식 게이트웨이로 옮긴 것이다(`decisions/109`).
 *
 * 브라우저 내장 음성 인식(Web Speech API)이 그 자리에서 글자로 바꿔 `WS /dev/text` 로 보낸다 — 오디오가
 * 서버로 오지 않아 **구글 STT·GCP 키·COST-1 캡과 무관**하다. 대신 품질은 브라우저 엔진 것이라
 * **배선 확인용이지 STT 품질 측정용이 아니다**(절대 원칙 2·10 — 이 경로의 결과를 수치로 인용하지 않는다).
 *
 * 토큰: 이 문은 DB 에 전사를 쓰므로 **과금 문과 같은 `GATEWAY_INGEST_TOKEN`** 을 요구한다. 브라우저는
 * 헤더를 못 붙이므로 서브프로토콜(`bearer.<토큰>`)로 낸다 — URL 에 싣지 않는다. 페이지에는 비밀이 없고,
 * 개발자가 붙여 넣은 값은 이 탭의 sessionStorage 에만 둔다. 이 머신(루프백)에서 열면 토큰 없이 된다.
 *
 * 크롬(폰·PC) 기준. 마이크 권한은 HTTPS 또는 localhost 에서만 열린다 — 운영
 * `https://server.solidbob.cloud/gateway/dev` 는 이미 HTTPS 라 터널(ngrok)이 필요 없다.
 */
import { createHash } from "node:crypto";

export const DEV_PAGE_HTML = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CallGuard 게이트웨이 — 개발용 테스트 통화</title>
<style>
  body { font: 15px/1.5 system-ui, sans-serif; margin: 0; padding: 16px; background: #f6f7f9; color: #1d2330; }
  main { max-width: 560px; margin: 0 auto; }
  h1 { font-size: 18px; margin: 0 0 4px; }
  p.note { color: #5a6272; font-size: 13px; margin: 0 0 16px; }
  label { display: block; font-size: 13px; color: #5a6272; margin: 12px 0 4px; }
  input, select, button { font: inherit; width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #c9ced8; border-radius: 8px; background: #fff; }
  button { margin-top: 16px; background: #1f5eff; color: #fff; border: 0; font-weight: 600; }
  button.stop { background: #d93636; }
  button:disabled { background: #9aa3b5; }
  #status { margin-top: 12px; font-size: 13px; }
  #log { margin-top: 12px; background: #fff; border: 1px solid #e1e4ea; border-radius: 8px; padding: 8px 10px; min-height: 120px; font-size: 14px; white-space: pre-wrap; }
  .interim { color: #8a93a5; }
</style>
</head>
<body>
<main>
  <h1>개발용 테스트 통화</h1>
  <p class="note">브라우저 음성 인식이 글자로 바꿔 게이트웨이로 보냅니다. 서버가 마스킹한 결과만 대시보드에 뜹니다.
  구글 STT 가 아니므로 <b>품질 측정용이 아닙니다</b>. 크롬에서 여세요.</p>

  <label for="token">게이트웨이 입력 토큰 (GATEWAY_INGEST_TOKEN — 이 탭에만 보관, 이 머신에서 열면 비워도 됩니다)</label>
  <input id="token" type="password" autocomplete="off" spellcheck="false">

  <label for="speaker">화자</label>
  <select id="speaker"><option value="customer">고객</option><option value="agent">상담원</option></select>

  <label for="callId">통화 ID (test- 로 시작 — 운영 DB 에 남습니다)</label>
  <input id="callId" spellcheck="false">

  <button id="start">통화 시작</button>
  <div id="status">대기 중</div>
  <div id="log"></div>
</main>
<script>
(() => {
  const $ = (id) => document.getElementById(id);
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
  $("callId").value = "test-web-" + stamp;
  try { $("token").value = sessionStorage.getItem("callguard:ingestToken") || ""; } catch (e) {}

  // /gateway/dev 로 열었으면 같은 접두어로 붙는다(운영 Ingress 경로).
  const prefix = location.pathname.startsWith("/gateway/") ? "/gateway" : "";
  let ws = null, rec = null, running = false, interimLine = null;

  const setStatus = (t) => { $("status").textContent = t; };
  const logLine = (text, interim) => {
    if (interim) {
      if (!interimLine) { interimLine = document.createElement("div"); interimLine.className = "interim"; $("log").appendChild(interimLine); }
      interimLine.textContent = "… " + text;
    } else {
      if (interimLine) { interimLine.remove(); interimLine = null; }
      const line = document.createElement("div"); line.textContent = "✓ " + text; $("log").appendChild(line);
    }
  };

  if (!Recognition) {
    setStatus("이 브라우저는 음성 인식(Web Speech API)을 지원하지 않습니다. 크롬으로 여세요.");
    $("start").disabled = true;
    return;
  }

  function stop(reason) {
    running = false;
    if (rec) { try { rec.stop(); } catch (e) {} rec = null; }
    if (ws && ws.readyState === WebSocket.OPEN) { ws.send(JSON.stringify({ type: "end" })); }
    $("start").textContent = "통화 시작"; $("start").className = "";
    setStatus(reason || "종료");
  }

  function start() {
    const token = $("token").value.trim();
    try { sessionStorage.setItem("callguard:ingestToken", token); } catch (e) {}
    const q = new URLSearchParams({ call_id: $("callId").value.trim(), speaker: $("speaker").value });
    const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + prefix + "/dev/text?" + q;
    // 토큰은 URL 이 아니라 서브프로토콜로 — 서버는 "callguard" 만 되돌려 준다.
    ws = token ? new WebSocket(url, ["callguard", "bearer." + token]) : new WebSocket(url);
    setStatus("게이트웨이에 연결 중…");
    ws.onopen = () => {
      running = true;
      $("start").textContent = "통화 종료"; $("start").className = "stop";
      setStatus("듣는 중 — 말하세요");
      rec = new Recognition();
      rec.lang = "ko-KR"; rec.continuous = true; rec.interimResults = true;
      rec.onresult = (event) => {
        let interim = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const text = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            if (text.trim()) { ws.send(JSON.stringify({ text, is_final: true })); logLine(text, false); }
          } else {
            interim += text;
          }
        }
        if (interim.trim()) { ws.send(JSON.stringify({ text: interim, is_final: false })); logLine(interim, true); }
      };
      rec.onerror = (e) => { if (e.error === "not-allowed") stop("마이크 권한이 거부됐습니다"); };
      // 크롬은 조용하면 인식을 스스로 멈춘다 — 통화 중이면 다시 켠다.
      rec.onend = () => { if (running) { try { rec.start(); } catch (e) {} } };
      rec.start();
    };
    ws.onclose = (e) => {
      if (running) stop("연결이 끊겼습니다 (" + e.code + (e.reason ? " " + e.reason : "") + ")");
      else if (e.code !== 1000) setStatus("연결 실패 (" + e.code + (e.reason ? " " + e.reason : "") + ") — 토큰을 확인하세요");
    };
  }

  $("start").onclick = () => (running ? stop() : start());
})();
</script>
</body>
</html>
`;

/**
 * 페이지 응답 헤더. API·Swagger 와 같은 도메인(`server.solidbob.cloud`)에서 나가므로 좁게 묶는다
 * (a5 세션 검토, 2026-09-11). 인라인 스크립트는 `unsafe-inline` 이 아니라 **해시**로만 허용한다.
 * `frame-ancestors 'none'` — 토큰을 붙여 넣은 탭을 남의 페이지가 틀에 넣고 «통화 시작» 을 누르게 하지 못한다.
 */
function scriptHash(html: string): string {
  const match = /<script>([\s\S]*?)<\/script>/.exec(html);
  if (match === null || match[1] === undefined) {
    throw new Error("dev 페이지에 인라인 스크립트가 없다");
  }
  return `'sha256-${createHash("sha256").update(match[1]).digest("base64")}'`;
}

export const DEV_PAGE_HEADERS: Record<string, string> = {
  "content-type": "text/html; charset=utf-8",
  "content-security-policy": [
    "default-src 'none'",
    `script-src ${scriptHash(DEV_PAGE_HTML)}`,
    "style-src 'unsafe-inline'",
    "connect-src 'self'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
  ].join("; "),
  "cache-control": "no-store",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
  "x-frame-options": "DENY",
};
