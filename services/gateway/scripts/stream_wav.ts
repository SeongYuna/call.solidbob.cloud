// Requirement: A-1, A-2
/**
 * WAV 파일을 **실시간 속도로** 게이트웨이 `/ingest` 에 흘려 넣는다 — 통화를 흉내 내는 생산자.
 *
 *   node scripts/stream_wav.ts <파일.wav> [--speaker customer] [--call-id test-...] \
 *       [--url ws://localhost:8080] [--max-seconds 30] [--speed 1] [--watch]
 *
 * - 모노 → 연결 하나(`--speaker`). 스테레오 → **채널을 갈라 연결 둘**(0번 agent · 1번 customer,
 *   `channels=2`). 데모의 물리 2채널이 이 모양이다(A-2).
 * - `--max-seconds` 가 기본 30초다. 구글 스트리밍은 쓴 만큼 과금되고 일 캡이 600초다(COST-1).
 * - `--watch` 는 `/ws?call_id=` 를 함께 열어 **대시보드가 받는 것**(마스킹된 결과)을 찍는다.
 *   원문은 이 스크립트가 볼 방법이 없다 — 볼 수 있으면 SEC-1 이 뚫린 것이다.
 *
 * 자체 녹음은 쓰지 않는다(절대 원칙 7) — AI Hub 처럼 출처가 해결된 음성만 넣는다.
 *
 * 이 머신 밖 게이트웨이에 붙을 때는 환경변수 `GATEWAY_INGEST_TOKEN`(과금 문)·`GATEWAY_VIEW_TOKEN`(`--watch`)을
 * **헤더로** 보낸다. 명령줄 인자로 받지 않는다 — 셸 기록에 비밀이 남는다.
 */
import { readFile } from "node:fs/promises";
import { WebSocket } from "ws";

interface Args {
  file: string;
  speaker: "agent" | "customer";
  callId: string;
  url: string;
  maxSeconds: number;
  speed: number;
  watch: boolean;
}

interface Wav {
  sampleRate: number;
  channels: number;
  pcm: Buffer;
}

const CHUNK_MS = 100;

function parseArgs(argv: string[]): Args {
  const args: Args = {
    file: "",
    speaker: "customer",
    callId: `test-${Date.now()}`,
    url: "ws://localhost:8080",
    maxSeconds: 30,
    speed: 1,
    watch: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    const value = argv[i + 1] ?? "";
    if (flag === "--speaker" && (value === "agent" || value === "customer")) {
      args.speaker = value;
      i += 1;
    } else if (flag === "--call-id") {
      args.callId = value;
      i += 1;
    } else if (flag === "--url") {
      args.url = value.replace(/\/+$/, "");
      i += 1;
    } else if (flag === "--max-seconds") {
      args.maxSeconds = Number(value);
      i += 1;
    } else if (flag === "--speed") {
      args.speed = Number(value);
      i += 1;
    } else if (flag === "--watch") {
      args.watch = true;
    } else if (flag !== undefined && !flag.startsWith("--")) {
      args.file = flag;
    }
  }
  if (args.file === "") {
    throw new Error("WAV 파일 경로가 없다");
  }
  return args;
}

/** RIFF/WAVE, PCM 16비트만 받는다. 구글에 LINEAR16 으로 그대로 넘기려는 것이다. */
function parseWav(buffer: Buffer): Wav {
  if (buffer.toString("ascii", 0, 4) !== "RIFF" || buffer.toString("ascii", 8, 12) !== "WAVE") {
    throw new Error("WAV(RIFF) 파일이 아니다");
  }
  let offset = 12;
  let sampleRate = 0;
  let channels = 0;
  let bits = 0;
  while (offset + 8 <= buffer.length) {
    const id = buffer.toString("ascii", offset, offset + 4);
    const size = buffer.readUInt32LE(offset + 4);
    const body = offset + 8;
    if (id === "fmt ") {
      const format = buffer.readUInt16LE(body);
      channels = buffer.readUInt16LE(body + 2);
      sampleRate = buffer.readUInt32LE(body + 4);
      bits = buffer.readUInt16LE(body + 14);
      if (format !== 1 || bits !== 16) {
        throw new Error(`PCM 16비트만 받는다 (format=${format}, bits=${bits})`);
      }
    } else if (id === "data") {
      if (sampleRate === 0) {
        throw new Error("fmt 청크가 data 보다 뒤에 있다");
      }
      return { sampleRate, channels, pcm: buffer.subarray(body, body + size) };
    }
    offset = body + size + (size % 2);
  }
  throw new Error("data 청크가 없다");
}

/** 인터리브된 스테레오에서 채널 하나를 뽑는다. */
function channelOf(wav: Wav, index: number): Buffer {
  if (wav.channels === 1) {
    return wav.pcm;
  }
  const frames = Math.floor(wav.pcm.length / (2 * wav.channels));
  const out = Buffer.alloc(frames * 2);
  for (let frame = 0; frame < frames; frame += 1) {
    out.writeInt16LE(wav.pcm.readInt16LE((frame * wav.channels + index) * 2), frame * 2);
  }
  return out;
}

function open(url: string, token = ""): Promise<WebSocket> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url, token ? { headers: { authorization: `Bearer ${token}` } } : {});
    ws.once("unexpected-response", (_req, res) => reject(new Error(`게이트웨이가 거절했다 (HTTP ${res.statusCode})`)));
    ws.once("open", () => resolve(ws));
    ws.once("error", reject);
  });
}

async function streamChannel(args: Args, wav: Wav, speaker: "agent" | "customer", pcm: Buffer, channelCount: number): Promise<void> {
  const query = new URLSearchParams({
    call_id: args.callId,
    speaker,
    sample_rate: String(wav.sampleRate),
    channels: String(channelCount),
  });
  const ws = await open(`${args.url}/ingest?${query}`, process.env.GATEWAY_INGEST_TOKEN ?? "");
  const closed = new Promise<{ code: number; reason: string }>((resolve) =>
    ws.once("close", (code, reason) => resolve({ code, reason: reason.toString() })),
  );
  const bytesPerChunk = Math.round((wav.sampleRate * 2 * CHUNK_MS) / 1000);
  const limit = Math.min(pcm.length, Math.round(args.maxSeconds * wav.sampleRate) * 2);
  const started = Date.now();
  let sent = 0;
  for (let offset = 0, n = 0; offset < limit && ws.readyState === ws.OPEN; offset += bytesPerChunk, n += 1) {
    const chunk = pcm.subarray(offset, Math.min(offset + bytesPerChunk, limit));
    ws.send(chunk);
    sent += chunk.byteLength;
    // 실시간 속도를 지킨다 — 누적 시각 기준이라 setTimeout 오차가 쌓이지 않는다.
    const due = started + ((n + 1) * CHUNK_MS) / args.speed;
    await new Promise((resolve) => setTimeout(resolve, Math.max(0, due - Date.now())));
  }
  if (ws.readyState === ws.OPEN) {
    ws.send(JSON.stringify({ type: "end" }));
  }
  const result = await closed;
  // 게이트웨이가 먼저 닫으면(한도·거절) 마지막 몇 청크는 소켓에 들어갔어도 STT 로는 안 갔다.
  const seconds = (sent / (wav.sampleRate * 2)).toFixed(1);
  console.log(`[${speaker}] ${seconds}초 보냄 — 닫힘 ${result.code}${result.reason ? ` (${result.reason})` : ""}`);
}

function watch(args: Args): Promise<WebSocket> {
  const url = `${args.url}/ws?call_id=${encodeURIComponent(args.callId)}`;
  return open(url, process.env.GATEWAY_VIEW_TOKEN ?? "").then((ws) => {
    const started = Date.now();
    ws.on("message", (data) => {
      const message = JSON.parse(data.toString()) as { type: string; payload: Record<string, unknown> };
      const at = `+${((Date.now() - started) / 1000).toFixed(2)}s`;
      if (message.type === "transcript") {
        const p = message.payload;
        const kind = p["is_final"] === "true" ? "FINAL  " : "interim";
        console.log(`${at} ${kind} #${String(p["segment_id"])} [${String(p["speaker"])}] ${String(p["text"])}`);
      } else if (message.type === "recommendation") {
        const p = message.payload;
        const cards = Array.isArray(p["cards"]) ? (p["cards"] as Array<{ title?: string }>).map((c) => c.title) : [];
        console.log(`${at} 추천 fired=${String(p["fired"])} cards=${JSON.stringify(cards)}`);
      }
    });
    return ws;
  });
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  const wav = parseWav(await readFile(args.file));
  console.log(
    `${args.file}: ${wav.channels}ch ${wav.sampleRate}Hz ${(wav.pcm.length / (wav.sampleRate * 2 * wav.channels)).toFixed(1)}초 → call_id=${args.callId}`,
  );
  const watcher = args.watch ? await watch(args) : null;
  if (wav.channels === 2) {
    await Promise.all([
      streamChannel(args, wav, "agent", channelOf(wav, 0), 2),
      streamChannel(args, wav, "customer", channelOf(wav, 1), 2),
    ]);
  } else if (wav.channels === 1) {
    await streamChannel(args, wav, args.speaker, wav.pcm, 1);
  } else {
    throw new Error(`채널 ${wav.channels}개는 받지 않는다 — 1(모노) 또는 2(물리 분리)`);
  }
  if (watcher !== null) {
    await new Promise((resolve) => setTimeout(resolve, 3000)); // 추천 응답을 조금 기다린다
    watcher.close();
  }
}

main().catch((error: unknown) => {
  console.error(`실패: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});
