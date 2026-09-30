// Requirement: A-3, B, C-5, C-1, C-6, F-2, J-1
/**
 * 시연 통화 — 마이크 없이 글자 채널(`/dev/text`)로 대본을 한 줄씩 흘린다. 발신 번호를 헤더로 실어
 * 블랙리스트 요청(J-1)·배정 판정(J-5)까지 한 통화에서 보인다. 판정은 상담원 화면을 보는 사람이 한다(`decisions/319`).
 *
 * 실행 (이 디렉터리에서 — `ws` 패키지를 쓴다):
 *   $env:CALL_MEDIATOR_INGEST_TOKEN='<입력 토큰>'; node scripts/demo_text_call.mjs [act1|act2] [--auto] [--call-id <id>] [--phone 010-0000-0901]
 *
 *   act1 (기본) — 인사 → 초본 문의(필요서류 카드) → 개인정보 7종 마스킹 → 폭언·위협(콜 가드) → 상담원 위반 셋(컴플라이언스)
 *                 → 상담원 서류 안내(체크리스트 1/1) → 과탐지 없음. 화면에서 통화 종료·요약·블랙리스트 요청은 사람이 누른다.
 *   act2         — 같은 발신 번호로 다시 건다(관리자가 승인한 뒤). 통화 시작 직후 「배정 판정 기록됨」 배너가 뜬다.
 *   --auto       — Enter 없이 줄마다 정해진 간격으로 보낸다(녹화용). 없으면 Enter 로 한 줄씩.
 *
 * 토큰은 채팅·문서·커밋에 붙여 넣지 않는다. 발신 번호는 실존하지 않는 `010-0000-XXXX` 만 쓴다.
 */
import readline from "node:readline/promises";
import { stdin, stdout } from "node:process";
import { WebSocket } from "ws";

const BASE = process.env.CALL_MEDIATOR_URL ?? "wss://server.solidbob.cloud/call-mediator";
const TOKEN = (process.env.CALL_MEDIATOR_INGEST_TOKEN ?? "").trim();
const args = process.argv.slice(2);
const ACT = args.includes("act2") ? "act2" : "act1";
const AUTO = args.includes("--auto");
const argOf = (flag, fallback) => {
  const i = args.indexOf(flag);
  return i !== -1 && args[i + 1] ? args[i + 1] : fallback;
};
const stamp = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 12);
const CALL_ID = argOf("--call-id", `demo-${ACT}-${stamp}`);
const PHONE = argOf("--phone", "010-0000-0901");

// [화자, 문장, 보낸 뒤 기다릴 초(auto 모드)] — 화면이 카드·경고를 그릴 시간을 둔다
const ACT1 = [
  ["agent", "안녕하세요 다산콜센터입니다 무엇을 도와드릴까요", 4],
  ["customer", "주민등록초본을 떼려고 하는데 뭐가 필요해요?", 8],
  ["agent", "네 초본 발급 안내해 드리겠습니다 본인 확인 먼저 할게요", 4],
  ["customer", "제 번호는 010-1234-5678이에요", 5],
  ["customer", "주민번호는 900101-1234567입니다", 5],
  ["customer", "카드번호는 1234 5678 9012 3456이요", 5],
  ["customer", "계좌는 110-123-456789예요", 5],
  ["customer", "인증번호 482913 불러드릴게요", 5],
  ["customer", "제 이름은 홍길동이고요 주소는 서울시 중구 세종대로 110 3층이에요", 6],
  ["customer", "이 멍청한 놈이 말귀를 못 알아듣네", 6],
  ["customer", "거기 찾아가서 가만 안 둔다 진짜", 6],
  ["agent", "지금 신청하시면 무조건 공제됩니다", 6],
  ["agent", "가족이니까 위임장까지는 없어도 되실 거예요", 6],
  ["agent", "주민등록번호 열세 자리 전부 불러 주세요", 6],
  ["agent", "신분증 챙겨 오시면 됩니다 주민센터에서 바로 발급됩니다", 8],
  ["customer", "서류 준비해서 오늘 안에 다 끝내고 싶어서요", 5],
  ["agent", "네 오늘 안에 가능합니다 더 도와드릴 것 없으시면 마치겠습니다", 4],
];
const ACT2 = [
  ["agent", "안녕하세요 다산콜센터입니다", 6],
  ["customer", "아까 전화했던 사람인데요 초본 말고 등본도 되나요", 8],
  ["agent", "네 등본도 같은 신분증으로 발급됩니다", 5],
];
const LINES = ACT === "act2" ? ACT2 : ACT1;
const LABEL = { agent: "상담원", customer: "고객" };

if (!TOKEN) {
  console.error("CALL_MEDIATOR_INGEST_TOKEN 이 비어 있습니다.");
  process.exit(1);
}

function open(speaker) {
  const q = new URLSearchParams({ call_id: CALL_ID, speaker, producer: "script" });
  const headers = { authorization: `Bearer ${TOKEN}`, "x-caller-phone": PHONE };
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(`${BASE}/dev/text?${q}`, { headers });
    ws.once("open", () => resolve(ws));
    ws.once("error", (e) => reject(new Error(`연결 실패 — ${e.message}`)));
    ws.on("close", (code, reason) => {
      if (code !== 1000) console.log(`  (연결 닫힘 ${code}${reason?.length ? " " + reason : ""})`);
    });
  });
}
function close(ws) {
  return new Promise((resolve) => {
    if (ws.readyState !== WebSocket.OPEN) return resolve();
    const timer = setTimeout(resolve, 3000);
    ws.once("close", () => { clearTimeout(timer); resolve(); });
    ws.send(JSON.stringify({ type: "end" }));
  });
}
const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));

const rl = AUTO ? null : readline.createInterface({ input: stdin, output: stdout });
console.log(`통화 ID: ${CALL_ID} · 발신 번호: ${PHONE} · ${ACT} · ${AUTO ? "자동 간격" : "Enter 로 진행"}`);
console.log(`상담원 화면: https://call.solidbob.cloud/?call_id=${CALL_ID}  ← 먼저 열어 두세요\n`);

// 화자별 채널을 열어 두고 끝까지 유지한다 — 실제 2채널 통화와 같다(0.2.12 부터는 닫혀도 5분 유예가 있다).
const channels = new Map();
try {
  for (const [speaker, text, wait] of LINES) {
    if (!AUTO) {
      const a = (await rl.question(`${LABEL[speaker]}: ${text}  ▶ `)).trim().toLowerCase();
      if (a === "q") break;
      if (a === "s") continue;
    } else {
      console.log(`${LABEL[speaker]}: ${text}`);
    }
    if (!channels.has(speaker)) channels.set(speaker, await open(speaker));
    channels.get(speaker).send(JSON.stringify({ text, is_final: true }));
    if (AUTO) await sleep(wait);
  }
  if (!AUTO) await rl.question("모두 보냈습니다. Enter 를 누르면 채널을 닫습니다 ▶ ");
  else await sleep(3);
} catch (err) {
  console.error(`중단: ${err.message}`);
} finally {
  for (const ch of channels.values()) await close(ch);
  rl?.close();
  console.log("끝. 통화 종료·요약·블랙리스트 요청은 상담원 화면 버튼으로 합니다.");
}
