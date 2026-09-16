// Requirement: A-1, A-3, C-5, C-6, J-5
/**
 * 합성 통화 대본(`scripts/persona_sim/dasan-v0/SYN-*.json`)을 게이트웨이 `/dev/text` 로 **실제 통화처럼** 흘린다.
 * 상담원 대시보드(`apps/call`, 라이브 모드)는 받는 메시지가 실제 통화와 같으니 **프론트를 고치지 않고** 그대로 그린다.
 *
 *   node scripts/replay_persona_call.ts --list
 *   node scripts/replay_persona_call.ts SYN-004 [--url ws://localhost:8080] [--speak] [--watch] [--speed 1] [--dry-run]
 *
 * - 두 화자를 **채널 둘**로 연다(`speaker=agent` · `speaker=customer`, `channels=2`) — 데모의 물리 2채널과 같은 모양이다.
 * - 턴마다 부분 결과(`is_final:false`)를 어절째 늘려 보내고 끝에 확정을 보낸다(`persona_replay/plan.ts`).
 * - `--speak` 는 이 맥에서 `say` 로 소리를 낸다(무료, 키 없음). 음성은 `personas.json` 의 `say_voice`, 없으면 `Yuna`.
 *   톤(`tone`)은 말하는 속도로만 흉내 낸다 — **D-5 통화 온도의 성능 근거가 아니다**(절대 원칙 10).
 * - `--watch` 는 `/ws?call_id=` 를 함께 열어 대시보드가 받는 것(마스킹된 자막·카드·콜 가드·필요서류)을 찍는다.
 * - 통화 기록 엔진은 `synthetic-script` 로 남는다(`producer=script`). STT 를 거치지 않았으므로 **여기서 나온 검색·마스킹
 *   수치는 상한이고, 지연 시각은 지어낸 값이다.**
 *
 * 토큰은 `stream_wav.ts` 와 같다 — 환경변수 `GATEWAY_INGEST_TOKEN`(글자 입력 문) · `GATEWAY_VIEW_TOKEN`(`--watch`)을
 * **헤더로** 보낸다. 명령줄 인자로 받지 않는다(셸 기록에 남는다).
 *
 * 발신 번호는 대본의 `caller_number`(실존하지 않는 `010-0000-XXXX`)를 `X-Caller-Phone` 헤더로 싣는다 — 같은 번호를 쓰는
 * SYN-006(블랙리스트 요청) → SYN-007(베테랑 배정) 이 한 고객으로 이어진다(`decisions/304`). 환경변수 `CALLER_PHONE` 이
 * 있으면 그것이 이긴다. **실제 시민 번호를 넣지 않는다.**
 */
import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { WebSocket } from "ws";
import { gapBefore, planTurn, readTurns, sayRate, type ScriptTurn, type Speaker } from "./persona_replay/plan.ts";

const SCRIPTS_DIR = fileURLToPath(new URL("../../../scripts/persona_sim/dasan-v0/", import.meta.url));
const FALLBACK_VOICE = "Yuna";

interface Args {
  target: string;
  url: string;
  callId: string;
  speed: number;
  speak: boolean;
  watch: boolean;
  dryRun: boolean;
  list: boolean;
}

interface Persona {
  label?: string;
  say_voice?: string;
}

interface Script {
  id: string;
  title: string;
  length_class?: string;
  caller_number?: string;
  agent_persona?: string;
  customer_persona?: string;
  expected?: { j?: Record<string, unknown> };
  notes?: string[];
}

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, Math.max(0, ms)));

function parseArgs(argv: string[]): Args {
  const args: Args = {
    target: "",
    url: "ws://localhost:8080",
    callId: "",
    speed: 1,
    speak: false,
    watch: false,
    dryRun: false,
    list: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    const value = argv[i + 1] ?? "";
    if (flag === "--url") {
      args.url = value.replace(/\/+$/, "");
      i += 1;
    } else if (flag === "--call-id") {
      args.callId = value;
      i += 1;
    } else if (flag === "--speed") {
      args.speed = Number(value);
      i += 1;
    } else if (flag === "--speak") {
      args.speak = true;
    } else if (flag === "--watch") {
      args.watch = true;
    } else if (flag === "--dry-run") {
      args.dryRun = true;
    } else if (flag === "--list") {
      args.list = true;
    } else if (flag !== undefined && !flag.startsWith("--")) {
      args.target = flag;
    }
  }
  if (!(args.speed > 0)) {
    throw new Error("--speed 는 0 보다 커야 한다");
  }
  return args;
}

/** `SYN-004` 처럼 ID 만 주면 대본 폴더에서 찾고, 경로를 주면 그 파일을 읽는다. */
async function loadScript(target: string): Promise<{ script: Script; turns: ScriptTurn[] }> {
  const path = /^SYN-\d{3}$/i.test(target) ? `${SCRIPTS_DIR}${target.toUpperCase()}.json` : target;
  const raw: unknown = JSON.parse(await readFile(path, "utf-8"));
  return { script: raw as Script, turns: readTurns(raw) };
}

async function loadPersonas(): Promise<Record<string, Persona>> {
  try {
    const raw = JSON.parse(await readFile(`${SCRIPTS_DIR}personas.json`, "utf-8")) as {
      agents?: Record<string, Persona>;
      customers?: Record<string, Persona>;
    };
    return { ...raw.agents, ...raw.customers };
  } catch {
    return {};
  }
}

async function listScripts(): Promise<void> {
  const files = (await readdir(SCRIPTS_DIR)).filter((f) => /^SYN-\d{3}\.json$/.test(f)).sort();
  for (const file of files) {
    const { script, turns } = await loadScript(`${SCRIPTS_DIR}${file}`);
    const j = script.expected?.j ?? {};
    const flags = [j["blacklist_request"] === true ? "블랙리스트 요청" : "", j["routing"] === "veteran" ? "베테랑 배정" : ""]
      .filter(Boolean)
      .join(" · ");
    console.log(`${script.id}  ${String(turns.length).padStart(2)}턴  ${script.title}${flags ? `  [${flags}]` : ""}`);
  }
}

/**
 * 이 맥에 설치된 **한국어** `say` 음성 — 짧은 이름(`Eddy`) → `say -v` 에 넘길 전체 이름(`Eddy (한국어(한국))`).
 * 같은 짧은 이름의 영어 음성이 따로 있어서 짧은 이름으로 부르면 영어 목소리가 한국어를 읽는다. `say` 가 없으면 null.
 */
function installedKoreanVoices(): Map<string, string> | null {
  if (process.platform !== "darwin") {
    return null;
  }
  try {
    const out = execFileSync("say", ["-v", "?"], { encoding: "utf-8" });
    const voices = new Map<string, string>();
    for (const line of out.split("\n")) {
      const match = /^(.+?)\s{2,}ko_KR\b/.exec(line);
      const full = match?.[1]?.trim();
      if (full) {
        voices.set(full.replace(/\s*\(.*\)$/, ""), full);
      }
    }
    return voices;
  } catch {
    return null;
  }
}

function open(url: string, headers: Record<string, string>): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url, { headers });
    ws.once("unexpected-response", (_req, res) => reject(new Error(`게이트웨이가 거절했다 (HTTP ${res.statusCode}) — ${url.split("?")[0]}`)));
    ws.once("open", () => resolve(ws));
    ws.once("error", reject);
  });
}

function bearer(token: string | undefined): Record<string, string> {
  const value = (token ?? "").trim();
  return value ? { authorization: `Bearer ${value}` } : {};
}

function watch(args: Args, callId: string): Promise<WebSocket> {
  return open(`${args.url}/ws?call_id=${encodeURIComponent(callId)}`, bearer(process.env.GATEWAY_VIEW_TOKEN)).then((ws) => {
    ws.on("message", (data) => {
      const message = JSON.parse(data.toString()) as { type: string; payload: Record<string, unknown> };
      const p = message.payload;
      if (message.type === "transcript" && p["is_final"] === "true") {
        console.log(`    ↳ 자막 [${String(p["speaker"])}] ${String(p["text"])}`);
      } else if (message.type === "recommendation") {
        const cards = Array.isArray(p["cards"]) ? (p["cards"] as Array<{ title?: string }>).map((c) => c.title) : [];
        console.log(`    ↳ 추천 fired=${String(p["fired"])} ${cards.length ? JSON.stringify(cards) : ""}`);
      } else if (message.type !== "transcript") {
        console.log(`    ↳ ${message.type} ${JSON.stringify(p).slice(0, 160)}`);
      }
    });
    return ws;
  });
}

async function openSpeakers(args: Args, callId: string, phone: string): Promise<Record<Speaker, WebSocket>> {
  const headers = { ...bearer(process.env.GATEWAY_INGEST_TOKEN), ...(phone ? { "x-caller-phone": phone } : {}) };
  const url = (speaker: Speaker): string =>
    `${args.url}/dev/text?${new URLSearchParams({ call_id: callId, speaker, channels: "2", producer: "script" })}`;
  // 상담원 채널이 통화를 연다(서버에 call 행). 고객 채널은 그 뒤 — 발신 번호는 처음 여는 채널 것만 간다.
  const agent = await open(url("agent"), headers);
  const customer = await open(url("customer"), headers);
  for (const [speaker, ws] of [["agent", agent], ["customer", customer]] as const) {
    ws.once("close", (code, reason) => {
      if (code !== 1000) {
        console.error(`[${speaker}] 게이트웨이가 닫았다 ${code} ${reason.toString()}`);
      }
    });
  }
  return { agent, customer };
}

function speak(text: string, voice: string, rate: number): ChildProcess {
  return spawn("say", ["-v", voice, "-r", String(rate), text], { stdio: "ignore" });
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  if (args.list) {
    await listScripts();
    return;
  }
  if (args.target === "") {
    throw new Error("대본 ID(SYN-004) 또는 JSON 경로가 없다 — --list 로 목록을 본다");
  }
  const { script, turns } = await loadScript(args.target);
  const personas = await loadPersonas();
  const callId = args.callId || `${script.id.toLowerCase()}-${Date.now()}`;
  const phone = (process.env.CALLER_PHONE ?? script.caller_number ?? "").trim();

  let voices = args.speak ? installedKoreanVoices() : null;
  if (args.speak && (voices === null || !voices.has(FALLBACK_VOICE))) {
    console.warn(`--speak 는 macOS say 와 한국어 음성(${FALLBACK_VOICE})이 있어야 한다 — 소리 없이 흘린다`);
    voices = null;
  }
  const voiceOf = (speaker: Speaker): string => {
    const id = speaker === "agent" ? script.agent_persona : script.customer_persona;
    const wanted = id ? personas[id]?.say_voice : undefined;
    return voices?.get(wanted ?? "") ?? voices?.get(FALLBACK_VOICE) ?? FALLBACK_VOICE;
  };

  console.log(`${script.id} ${script.title} — ${turns.length}턴 → call_id=${callId}${args.dryRun ? " (dry-run)" : ""}`);
  const j = script.expected?.j ?? {};
  if (j["precondition"]) {
    console.log(`  ⚠ 전제: ${String(j["precondition"])}`);
  }

  const watcher = args.watch && !args.dryRun ? await watch(args, callId) : null;
  const sockets = args.dryRun ? null : await openSpeakers(args, callId, phone);
  let stopped = false;
  process.once("SIGINT", () => {
    stopped = true;
  });

  let previous: ScriptTurn | undefined;
  for (const turn of turns) {
    if (stopped) {
      break;
    }
    await sleep(gapBefore(previous, turn, args.speed));
    previous = turn;
    const plan = planTurn(turn, args.speed);
    const ws = sockets?.[turn.speaker];
    const send = (text: string, isFinal: boolean): void => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ text, is_final: isFinal }));
      }
    };
    console.log(`#${String(turn.seq).padStart(2)} [${turn.speaker === "agent" ? "상담원" : "고객  "}|${turn.tone}] ${turn.text}`);

    const started = Date.now();
    const voice = voices !== null ? speak(turn.text, voiceOf(turn.speaker), Math.round(sayRate(turn.tone) * args.speed)) : null;
    const spoken = voice ? new Promise<void>((resolve) => voice.once("exit", () => resolve())) : Promise.resolve();
    for (const interim of plan.interims) {
      await sleep(started + interim.offsetMs - Date.now());
      send(interim.text, false);
    }
    // 소리가 계획보다 길면 소리가 끝날 때 확정한다 — 자막이 말보다 먼저 굳지 않게.
    await Promise.all([sleep(started + plan.durationMs - Date.now()), spoken]);
    send(turn.text, true);
  }

  if (sockets !== null) {
    const closed = Object.values(sockets).map(
      (ws) => new Promise<void>((resolve) => (ws.readyState === WebSocket.CLOSED ? resolve() : ws.once("close", () => resolve()))),
    );
    for (const ws of Object.values(sockets)) {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "end" }));
      }
    }
    await Promise.race([Promise.all(closed), sleep(10_000)]);
  }
  if (watcher !== null) {
    await sleep(3000); // 마지막 추천·필요서류 판정을 조금 기다린다
    watcher.close();
  }
  if (j["blacklist_request"] === true) {
    console.log("  → 이 대본은 통화 뒤 상담원이 「블랙리스트 전환 요청」을 누르는 시나리오다(J-1, 대시보드에서 사람이 누른다)");
  }
  if (j["routing"] === "veteran") {
    console.log("  → 이 대본은 같은 번호가 active 일 때 베테랑 배정(J-5)을 보여 주는 시나리오다 — 배정 판정은 서버 API 몫이다");
  }
}

main().catch((error: unknown) => {
  console.error(`실패: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
