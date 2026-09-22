// Requirement: A-1, A-3, C-5, C-6, J-5
/**
 * 합성 통화 대본(`scripts/persona_sim/dasan-v0/SYN-*.json`)을 콜 미디에이터 `/dev/text` 로 **실제 통화처럼** 흘린다.
 * 상담원 대시보드(`apps/call`, 라이브 모드)는 받는 메시지가 실제 통화와 같으니 **프론트를 고치지 않고** 그대로 그린다.
 *
 *   node scripts/replay_persona_call.ts --list
 *   node scripts/replay_persona_call.ts SYN-004 [--url ws://localhost:8080] [--speak [say|google]] [--watch] [--speed 1] [--dry-run]
 *       [--close --core-url http://localhost:8000]
 *   node scripts/replay_persona_call.ts --prefetch [SYN-004]      # 재생 없이 Google TTS 캐시만 채운다(전 대본 또는 하나)
 *
 * - 두 화자를 **채널 둘**로 연다(`speaker=agent` · `speaker=customer`, `channels=2`) — 데모의 물리 2채널과 같은 모양이다.
 * - 턴마다 부분 결과(`is_final:false`)를 어절째 늘려 보내고 끝에 확정을 보낸다(`persona_replay/plan.ts`).
 * - `--speak` / `--speak say` 는 이 맥에서 `say` 로 소리를 낸다(무료, 키 없음). 음성은 `personas.json` 의 `say_voice`, 없으면 `Yuna`.
 *   톤(`tone`)은 말하는 속도로만 흉내 낸다 — **D-5 통화 온도의 성능 근거가 아니다**(절대 원칙 10).
 * - `--speak google` 은 Google Cloud TTS(ko-KR WaveNet)로 낸다 — `persona_replay/google_tts.ts`. 재생 전에 대본 전체를
 *   캐시(`data/processed/synthetic-voice/google/`)에 채우고, 있는 것은 **API 를 부르지 않는다**. 키는 환경변수
 *   `GOOGLE_TTS_API_KEY` 뿐이고(`.env`), 월 문자 한도 `GOOGLE_TTS_MAX_CHARS_PER_MONTH`(기본 900,000)를 넘기면 부르기 전에 멈춘다
 *   (`persona_replay/tts_budget.ts`, COST-1 과 같은 2단 가드). 키가 없는데 캐시도 없으면 **`say` 로 조용히 넘어가지 않고** 실패한다.
 *   발급·설정·비용은 `scripts/persona_sim/TTS.md`.
 * - `--watch` 는 `/ws?call_id=` 를 함께 열어 대시보드가 받는 것(마스킹된 자막·카드·콜 가드·필요서류)을 찍는다.
 * - `--close --core-url <서버>` 는 재생이 끝나면 `POST /hub/calls/{id}/close` 로 통화 후 요약 초안을 만든다(D-1~D-3).
 *   본문에는 **`/ws` 로 받은 마스킹본만** 싣는다 — 대본 원문을 보내지 않는다(SEC-1). 그래서 `--watch` 와 같은 뷰 토큰이 필요하다.
 *   서버가 이 API 를 잠갔다(`decisions/315`) — 환경변수 `CORE_API_TOKEN`(콜 미디에이터가 서버에 쓰는 서비스 토큰과 같은 값)을
 *   헤더로 싣는다. 없으면 401 이다.
 * - 통화 기록 엔진은 `synthetic-script` 로 남는다(`producer=script`). STT 를 거치지 않았으므로 **여기서 나온 검색·마스킹
 *   수치는 상한이고, 지연 시각은 지어낸 값이다.**
 *
 * 토큰은 `stream_wav.ts` 와 같다 — 환경변수 `CALL_MEDIATOR_INGEST_TOKEN`(글자 입력 문) · `CALL_MEDIATOR_VIEW_TOKEN`(`--watch`)을
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
import { pickVoice } from "./persona_replay/google_voices.ts";
import {
  buildSsml,
  cacheStem,
  ENV_API_KEY,
  findPlayer,
  synthesizeToCache,
  TtsBudgetExceeded,
  type Player,
} from "./persona_replay/google_tts.ts";
import { capFromEnv, TtsBudget, TtsLedgerFile } from "./persona_replay/tts_budget.ts";

const REPO_ROOT = fileURLToPath(new URL("../../../", import.meta.url));
const SCRIPTS_DIR = `${REPO_ROOT}scripts/persona_sim/dasan-v0/`;
const FALLBACK_VOICE = "Yuna";
/** Google TTS 캐시·장부. `data/processed/` 는 gitignore 다. `GOOGLE_TTS_CACHE_DIR` 로 캐시 위치만 바꿀 수 있다. */
const TTS_CACHE_ROOT = (process.env.GOOGLE_TTS_CACHE_DIR ?? "").trim() || `${REPO_ROOT}data/processed/synthetic-voice/google`;
const TTS_LEDGER_PATH = `${REPO_ROOT}data/processed/tts-usage.json`;

type SpeakEngine = "off" | "say" | "google";

interface Args {
  target: string;
  url: string;
  callId: string;
  speed: number;
  speak: SpeakEngine;
  prefetch: boolean;
  watch: boolean;
  dryRun: boolean;
  list: boolean;
  close: boolean;
  coreUrl: string;
}

/** `/ws` 로 받은 확정 자막 — 서버가 마스킹해 돌려준 것. 통화 후 요약 요청에 이것만 싣는다. */
interface MaskedFinal {
  segment_id: number;
  speaker: Speaker;
  text: string;
  is_final: boolean;
  utterance_end_ms: number | null;
}

interface Persona {
  label?: string;
  say_voice?: string;
  tts_voice_hint?: string;
  google_tts_voice?: string;
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
    speak: "off",
    prefetch: false,
    watch: false,
    dryRun: false,
    list: false,
    close: false,
    coreUrl: "",
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
      // 값이 따라오면(say|google) 그것, 아니면 say — `--speak --watch` 처럼 다음 플래그가 오는 경우를 가른다
      if (value === "say" || value === "google") {
        args.speak = value;
        i += 1;
      } else if (value === "" || value.startsWith("--")) {
        args.speak = "say";
      } else {
        throw new Error(`--speak 는 say 또는 google 이다: ${value}`);
      }
    } else if (flag === "--prefetch") {
      args.prefetch = true;
    } else if (flag === "--watch") {
      args.watch = true;
    } else if (flag === "--dry-run") {
      args.dryRun = true;
    } else if (flag === "--list") {
      args.list = true;
    } else if (flag === "--close") {
      args.close = true;
    } else if (flag === "--core-url") {
      args.coreUrl = value.replace(/\/+$/, "");
      i += 1;
    } else if (flag !== undefined && !flag.startsWith("--")) {
      args.target = flag;
    }
  }
  if (!(args.speed > 0)) {
    throw new Error("--speed 는 0 보다 커야 한다");
  }
  if (args.close && args.coreUrl === "") {
    throw new Error("--close 는 --core-url(서버 주소)이 있어야 한다 — 콜 미디에이터 주소와 다르다");
  }
  if (args.prefetch && args.speak === "say") {
    throw new Error("--prefetch 는 Google TTS 캐시를 채우는 것이다 — --speak say 와 같이 쓸 수 없다");
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
    ws.once("unexpected-response", (_req, res) => reject(new Error(`콜 미디에이터가 거절했다 (HTTP ${res.statusCode}) — ${url.split("?")[0]}`)));
    ws.once("open", () => resolve(ws));
    ws.once("error", reject);
  });
}

function bearer(token: string | undefined): Record<string, string> {
  const value = (token ?? "").trim();
  return value ? { authorization: `Bearer ${value}` } : {};
}

function watch(args: Args, callId: string, finals: Map<number, MaskedFinal>, print: boolean): Promise<WebSocket> {
  return open(`${args.url}/ws?call_id=${encodeURIComponent(callId)}`, bearer(process.env.CALL_MEDIATOR_VIEW_TOKEN)).then((ws) => {
    ws.on("message", (data) => {
      const message = JSON.parse(data.toString()) as { type: string; payload: Record<string, unknown> };
      const p = message.payload;
      if (message.type === "transcript" && p["is_final"] === "true") {
        // 계약상 전 필드가 문자열이다(§7.3) — 요약 요청 스키마의 숫자·불리언으로 되돌린다
        const endMs = Number(p["utterance_end_ms"]);
        finals.set(Number(p["segment_id"]), {
          segment_id: Number(p["segment_id"]),
          speaker: p["speaker"] === "agent" ? "agent" : "customer",
          text: String(p["text"]),
          is_final: true,
          utterance_end_ms: Number.isFinite(endMs) ? endMs : null,
        });
      }
      if (!print) {
        return;
      }
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
  const headers = { ...bearer(process.env.CALL_MEDIATOR_INGEST_TOKEN), ...(phone ? { "x-caller-phone": phone } : {}) };
  const url = (speaker: Speaker): string =>
    `${args.url}/dev/text?${new URLSearchParams({ call_id: callId, speaker, channels: "2", producer: "script" })}`;
  // 상담원 채널이 통화를 연다(서버에 call 행). 고객 채널은 그 뒤 — 발신 번호는 처음 여는 채널 것만 간다.
  const agent = await open(url("agent"), headers);
  const customer = await open(url("customer"), headers);
  for (const [speaker, ws] of [["agent", agent], ["customer", customer]] as const) {
    ws.once("close", (code, reason) => {
      if (code !== 1000) {
        console.error(`[${speaker}] 콜 미디에이터가 닫았다 ${code} ${reason.toString()}`);
      }
    });
  }
  return { agent, customer };
}

/** 통화 후 요약 초안(D-1~D-3). 마스킹본이 한 건도 없으면 부르지 않는다 — 원문으로 대신 채우지 않는다. */
async function closeCall(coreUrl: string, callId: string, segments: MaskedFinal[]): Promise<void> {
  if (segments.length === 0) {
    console.error("  → 통화 후 요약을 건너뛴다: /ws 로 받은 마스킹 자막이 0건이다(뷰 토큰·콜 미디에이터 확인)");
    process.exitCode = 1;
    return;
  }
  const res = await fetch(`${coreUrl}/hub/calls/${encodeURIComponent(callId)}/close`, {
    method: "POST",
    headers: { "content-type": "application/json", ...bearer(process.env.CORE_API_TOKEN) },
    body: JSON.stringify({ call_id: callId, segments }),
  });
  const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) {
    console.error(`  → 통화 후 요약 실패 HTTP ${res.status} ${JSON.stringify(body).slice(0, 200)}`);
    process.exitCode = 1;
    return;
  }
  const actions = Array.isArray(body["follow_up_actions"]) ? body["follow_up_actions"].length : 0;
  console.log(
    `  → 통화 후 요약 초안: 자막 ${segments.length}건 → 요약 ${String(body["summary_text"] ?? "").length}자 · 유형 제안 ${String(body["inquiry_type"] ?? "없음")} · 후속조치 ${actions}건 (확정 전)`,
  );
}

function speak(text: string, voice: string, rate: number): ChildProcess {
  return spawn("say", ["-v", voice, "-r", String(rate), text], { stdio: "ignore" });
}

function play(player: Player, file: string, rate: number): ChildProcess {
  return spawn(player.command, player.args(file, rate), { stdio: "ignore" });
}

function newBudget(): TtsBudget {
  return new TtsBudget(new TtsLedgerFile(TTS_LEDGER_PATH), capFromEnv(process.env));
}

/**
 * 대본 한 편의 턴 전부를 Google TTS 캐시에 채운다 — 있는 턴은 API 를 부르지 않는다. 돌려주는 값은 seq → mp3 경로.
 * 재생 **전에** 한꺼번에 하는 이유: 턴마다 합성하면 API 왕복(수백 ms)이 말 사이 틈으로 끼어 대화가 어색해진다.
 */
async function prepareGoogleAudio(
  script: Script,
  turns: ScriptTurn[],
  personas: Record<string, Persona>,
  budget: TtsBudget,
): Promise<Map<number, string>> {
  const apiKey = (process.env[ENV_API_KEY] ?? "").trim();
  const dir = `${TTS_CACHE_ROOT}/${script.id}`;
  const files = new Map<number, string>();
  let synthesized = 0;
  let cached = 0;
  let chars = 0;
  for (const turn of turns) {
    const personaId = turn.speaker === "agent" ? script.agent_persona : script.customer_persona;
    const choice = pickVoice(personaId, personas[personaId ?? ""] ?? {});
    const req = { ssml: buildSsml(turn.text, turn.tone), voice: choice.voice, pitch: choice.pitch };
    try {
      const out = await synthesizeToCache({ req, dir, stem: cacheStem(turn.seq, turn.speaker), apiKey, budget });
      files.set(turn.seq, out.path);
      if (out.cached) {
        cached += 1;
      } else {
        synthesized += 1;
        chars += out.chars;
      }
    } catch (error) {
      if (error instanceof TtsBudgetExceeded) {
        const usage = await budget.used();
        throw new Error(
          `${script.id} #${turn.seq} 에서 멈췄다 — ${error.message}. ` +
            `장부 ${usage.month}: ${usage.used.toLocaleString()}/${usage.cap.toLocaleString()}자 (${TTS_LEDGER_PATH})`,
        );
      }
      throw error;
    }
  }
  const usage = await budget.used();
  console.log(
    `  ♪ Google TTS ${script.id}: 캐시 ${cached} · 새로 합성 ${synthesized}(${chars.toLocaleString()}자) · ` +
      `이번 달 누계 ${usage.used.toLocaleString()}/${usage.cap.toLocaleString()}자`,
  );
  return files;
}

async function prefetch(target: string): Promise<void> {
  const ids = target === "" ? (await readdir(SCRIPTS_DIR)).filter((f) => /^SYN-\d{3}\.json$/.test(f)).map((f) => f.replace(/\.json$/, "")).sort() : [target];
  const personas = await loadPersonas();
  const budget = newBudget();
  if ((process.env[ENV_API_KEY] ?? "").trim() === "") {
    console.warn(`${ENV_API_KEY} 가 비어 있다 — 캐시에 이미 있는 턴만 확인하고, 없는 턴에서 멈춘다`);
  }
  for (const id of ids) {
    const { script, turns } = await loadScript(id);
    await prepareGoogleAudio(script, turns, personas, budget);
  }
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  if (args.list) {
    await listScripts();
    return;
  }
  if (args.prefetch) {
    await prefetch(args.target);
    return;
  }
  if (args.target === "") {
    throw new Error("대본 ID(SYN-004) 또는 JSON 경로가 없다 — --list 로 목록을 본다");
  }
  const { script, turns } = await loadScript(args.target);
  const personas = await loadPersonas();
  const callId = args.callId || `${script.id.toLowerCase()}-${Date.now()}`;
  const phone = (process.env.CALLER_PHONE ?? script.caller_number ?? "").trim();

  let voices = args.speak === "say" ? installedKoreanVoices() : null;
  if (args.speak === "say" && (voices === null || !voices.has(FALLBACK_VOICE))) {
    console.warn(`--speak 는 macOS say 와 한국어 음성(${FALLBACK_VOICE})이 있어야 한다 — 소리 없이 흘린다`);
    voices = null;
  }
  // Google TTS — 소켓을 열기 전에 캐시를 채운다(키·예산·플레이어 문제로 실패하면 통화 행이 생기기 전에 멈춘다)
  let player: Player | null = null;
  let googleFiles = new Map<number, string>();
  if (args.speak === "google" && args.dryRun) {
    console.log("  ♪ dry-run 이라 Google TTS 도 부르지 않는다 — 캐시를 채우려면 --prefetch");
  } else if (args.speak === "google") {
    player = findPlayer();
    if (player === null) {
      throw new Error("--speak google 은 afplay(macOS) 또는 ffplay 가 있어야 한다");
    }
    googleFiles = await prepareGoogleAudio(script, turns, personas, newBudget());
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

  const finals = new Map<number, MaskedFinal>();
  const watcher = (args.watch || args.close) && !args.dryRun ? await watch(args, callId, finals, args.watch) : null;
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
    const googleFile = googleFiles.get(turn.seq);
    const voice =
      player !== null && googleFile !== undefined
        ? play(player, googleFile, args.speed)
        : voices !== null
          ? speak(turn.text, voiceOf(turn.speaker), Math.round(sayRate(turn.tone) * args.speed))
          : null;
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
  if (args.close && !args.dryRun) {
    await closeCall(args.coreUrl, callId, [...finals.values()].sort((a, b) => a.segment_id - b.segment_id));
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
