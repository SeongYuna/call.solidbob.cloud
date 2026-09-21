// Requirement: A-5, D-5, COST-1
/**
 * Google Cloud Text-to-Speech(REST, 의존성 0) — 합성 통화 재생기의 **소리 쪽**. 글자는 여전히 `/dev/text` 로 간다.
 *
 * - 호출: `POST https://texttospeech.googleapis.com/v1/text:synthesize`, 키는 **`x-goog-api-key` 헤더**로만 보낸다
 *   (URL `?key=` 는 접근 로그·프록시에 남는다 — https://docs.cloud.google.com/docs/authentication/api-keys-use, 2026-09-18 확인).
 *   키는 환경변수 `GOOGLE_TTS_API_KEY` 에서만 읽고, 로그·오류 문구에 찍지 않는다(`redact`).
 * - 톤 → SSML `<prosody rate pitch volume>` — `personas.json` 의 `tones` 힌트 값 그대로. 문장 전체를 감싼다
 *   (구글 문서: prosody 는 문장 단위로 — 단어만 감싸면 원치 않는 쉼이 생긴다).
 * - 캐시 우선: `<cacheRoot>/<SYN-id>/<seq>-<speaker>.mp3` + `.json`(음성·지문·문자 수). 지문이 같으면 **API 를 부르지 않는다**
 *   — 시연 때는 호출 0 이 되는 게 정상이고, 키 없이도 재생된다.
 * - 과금 문자 수는 **SSML 전체 길이**다(태그·공백 포함, `<mark>` 만 제외 — 우리는 `<mark>` 를 안 쓴다). 가드(`tts_budget.ts`)가
 *   호출 전에 이 수로 판정한다. 요청당 5,000 바이트 상한(https://docs.cloud.google.com/text-to-speech/quotas)도 미리 막는다.
 *
 * ⚠ 이것으로 D-5 통화 온도의 성능을 말할 수 없다(절대 원칙 10) — 톤은 우리가 넣은 운율 지시지 사람의 격앙이 아니다.
 */
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import type { Speaker, Tone } from "./plan.ts";
import type { WavenetVoice } from "./google_voices.ts";
import type { TtsBudget } from "./tts_budget.ts";

export const TTS_ENDPOINT = "https://texttospeech.googleapis.com/v1/text:synthesize";
export const ENV_API_KEY = "GOOGLE_TTS_API_KEY";
/** 구글 요청당 입력 상한(바이트). 콘솔에서 올릴 수 없는 값이다. */
export const MAX_INPUT_BYTES = 5000;

export interface Prosody {
  rate?: string;
  pitch?: string;
  volume?: string;
}

/**
 * 톤 → SSML prosody. `personas.json` `tones` 힌트의 **의도(평온 대비 dB)** 를 실제로 들리는 값으로 옮긴 것이다.
 *
 * ⚠ **WaveNet 은 SSML `volume` 의 «올리기»(+dB)를 무시한다**(2026-09-21 실측 — 같은 문장·같은 음성에서
 * `volume="+8dB"` 만 준 합성이 평온과 평균·최대 음량까지 똑같았다. 평온 합성이 이미 최대치 근처(-2.5 dBFS)라
 * 더 키우면 찢어지기 때문으로 보인다). 내리기(-dB)와 `rate`·`pitch` 는 반영된다.
 * 그래서 **기준(평온)을 -8 dB 로 낮추고** 다른 톤을 그 위아래에 둔다 — 같은 실측에서
 * 평온 대비 격앙 +3.8 dB · 고함 +7.1 dB · 지침 -5.0 dB 가 나왔다(의도 +4·+8·-4).
 * 전체가 8 dB 작아지므로 시연 때 스피커 음량을 올린다.
 */
export const TONE_PROSODY: Record<Tone, Prosody> = {
  calm: { volume: "-8dB" },
  tense: { rate: "105%", pitch: "+1st", volume: "-8dB" },
  raised: { rate: "110%", pitch: "+3st", volume: "-4dB" },
  shouting: { rate: "115%", pitch: "+5st" },
  weary: { rate: "85%", pitch: "-2st", volume: "-12dB" },
};

export function escapeXml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
}

export function buildSsml(text: string, tone: Tone): string {
  const body = escapeXml(text.trim());
  const prosody = TONE_PROSODY[tone];
  const attrs = Object.entries(prosody)
    .map(([key, value]) => ` ${key}="${value}"`)
    .join("");
  return attrs === "" ? `<speak>${body}</speak>` : `<speak><prosody${attrs}>${body}</prosody></speak>`;
}

/** 과금 문자 수 — 코드포인트 단위(구글은 바이트가 아니라 문자로 센다). SSML 태그·공백 포함. */
export function billableChars(ssml: string): number {
  return [...ssml].length;
}

export interface SynthesisRequest {
  ssml: string;
  voice: WavenetVoice;
  /** 반음(-20~20). 0 이면 보내지 않는다. */
  pitch: number;
}

/** 캐시가 유효한지 가르는 지문 — 입력이 하나라도 바뀌면 다시 합성한다. */
export function fingerprint(req: SynthesisRequest): string {
  return createHash("sha256").update(JSON.stringify({ ssml: req.ssml, voice: req.voice, pitch: req.pitch, encoding: "MP3" })).digest("hex").slice(0, 24);
}

export function cacheStem(seq: number, speaker: Speaker): string {
  return `${String(seq).padStart(2, "0")}-${speaker}`;
}

export interface CacheEntry {
  voice: WavenetVoice;
  pitch: number;
  fingerprint: string;
  chars: number;
  synthesized_at: string;
}

export interface SynthesisOutcome {
  path: string;
  /** true 면 API 를 부르지 않았다. */
  cached: boolean;
  /** 이번에 청구된 문자 수. 캐시 히트는 0. */
  chars: number;
}

export class TtsBudgetExceeded extends Error {}

/** 비밀이 어디에 섞여도 문구에서 지운다 — 구글 오류 본문이 요청을 되비칠 수 있다. */
export function redact(message: string, secret: string): string {
  return secret.length === 0 ? message : message.split(secret).join("<redacted>");
}

async function readCache(jsonPath: string): Promise<CacheEntry | null> {
  try {
    return JSON.parse(await readFile(jsonPath, "utf-8")) as CacheEntry;
  } catch {
    return null;
  }
}

async function exists(path: string): Promise<boolean> {
  try {
    await readFile(path, { flag: "r" });
    return true;
  } catch {
    return false;
  }
}

export interface SynthesizeOptions {
  req: SynthesisRequest;
  dir: string;
  stem: string;
  /** 없으면(빈 문자열) 캐시만 본다 — 캐시가 없으면 실패한다. */
  apiKey: string;
  budget: TtsBudget;
  fetchImpl?: typeof fetch;
  now?: () => Date;
}

/** 캐시가 있으면 그것, 없으면 합성해 캐시에 넣는다. 예산 거절은 `TtsBudgetExceeded` 로 던진다 — 호출은 하지 않았다. */
export async function synthesizeToCache(options: SynthesizeOptions): Promise<SynthesisOutcome> {
  const { req, dir, stem, apiKey, budget } = options;
  const fetchImpl = options.fetchImpl ?? fetch;
  const mp3Path = join(dir, `${stem}.mp3`);
  const jsonPath = join(dir, `${stem}.json`);
  const print = fingerprint(req);

  const entry = await readCache(jsonPath);
  if (entry?.fingerprint === print && (await exists(mp3Path))) {
    return { path: mp3Path, cached: true, chars: 0 };
  }

  if (apiKey === "") {
    throw new Error(`${ENV_API_KEY} 가 비어 있고 캐시도 없다(${stem}) — 키를 .env 에 넣거나 --prefetch 를 먼저 돌린다`);
  }
  const bytes = Buffer.byteLength(req.ssml, "utf-8");
  if (bytes > MAX_INPUT_BYTES) {
    throw new Error(`${stem}: SSML 이 ${bytes} 바이트 — 구글 요청당 상한 ${MAX_INPUT_BYTES} 바이트를 넘는다. 턴을 나눈다`);
  }
  const chars = billableChars(req.ssml);
  const decision = await budget.decide(chars);
  if (!decision.ok) {
    throw new TtsBudgetExceeded(`${stem}: ${decision.reason}`);
  }

  const body = {
    input: { ssml: req.ssml },
    voice: { languageCode: "ko-KR", name: req.voice },
    audioConfig: { audioEncoding: "MP3", ...(req.pitch === 0 ? {} : { pitch: req.pitch }) },
  };
  let res: Response;
  try {
    res = await fetchImpl(TTS_ENDPOINT, {
      method: "POST",
      headers: { "content-type": "application/json; charset=utf-8", "x-goog-api-key": apiKey },
      body: JSON.stringify(body),
    });
  } catch (error) {
    throw new Error(`${stem}: Google TTS 요청 실패 — ${redact(error instanceof Error ? error.message : String(error), apiKey)}`);
  }
  if (!res.ok) {
    const text = redact((await res.text().catch(() => "")).slice(0, 300), apiKey);
    throw new Error(`${stem}: Google TTS HTTP ${res.status} — ${text}`);
  }
  const payload = (await res.json()) as { audioContent?: unknown };
  if (typeof payload.audioContent !== "string" || payload.audioContent.length === 0) {
    throw new Error(`${stem}: 응답에 audioContent 가 없다`);
  }

  await mkdir(dir, { recursive: true });
  await writeFile(mp3Path, Buffer.from(payload.audioContent, "base64"));
  const record: CacheEntry = {
    voice: req.voice,
    pitch: req.pitch,
    fingerprint: print,
    chars,
    synthesized_at: (options.now ?? (() => new Date()))().toISOString(),
  };
  await writeFile(jsonPath, `${JSON.stringify(record, null, 1)}\n`, "utf-8");
  await budget.charge(chars);
  return { path: mp3Path, cached: false, chars };
}

export interface Player {
  command: string;
  /** `rate` 는 재생 배속(`--speed`). afplay 만 받는다 — ffplay 는 1배속으로 튼다. */
  args(file: string, rate?: number): string[];
}

/** 이 머신에서 mp3 를 틀 수 있는 것 — macOS `afplay`, 없으면 `ffplay`. 둘 다 없으면 null. */
export function findPlayer(which: (command: string) => boolean = commandExists): Player | null {
  if (which("afplay")) {
    return { command: "afplay", args: (file, rate = 1) => (rate === 1 ? [file] : ["-r", String(rate), file]) };
  }
  if (which("ffplay")) {
    return { command: "ffplay", args: (file) => ["-nodisp", "-autoexit", "-loglevel", "quiet", file] };
  }
  return null;
}

function commandExists(command: string): boolean {
  try {
    execFileSync("which", [command], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}
