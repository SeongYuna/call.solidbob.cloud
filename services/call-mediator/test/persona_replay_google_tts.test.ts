// Requirement: A-5, D-5, COST-1
import assert from "node:assert/strict";
import { mkdtemp, readFile, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import {
  billableChars,
  buildSsml,
  cacheStem,
  escapeXml,
  findPlayer,
  fingerprint,
  MAX_INPUT_BYTES,
  redact,
  synthesizeToCache,
  TTS_ENDPOINT,
  TtsBudgetExceeded,
} from "../scripts/persona_replay/google_tts.ts";
import { FALLBACK_VOICE, PERSONA_VOICES, pickVoice, WAVENET_GENDER } from "../scripts/persona_replay/google_voices.ts";
import {
  capFromEnv,
  charge,
  decideSynthesis,
  DEFAULT_MAX_CHARS_PER_MONTH,
  localMonth,
  MemoryTtsLedger,
  TtsBudget,
  TtsLedgerFile,
  usedInMonth,
} from "../scripts/persona_replay/tts_budget.ts";

const KEY = "AIza-test-secret-key-000";
const MP3 = Buffer.from("ID3fake-mp3-bytes").toString("base64");

function fakeFetch(calls: Array<{ url: string; headers: Record<string, string>; body: unknown }>, status = 200, text = "") {
  const impl = async (url: string | URL | Request, init?: RequestInit): Promise<Response> => {
    calls.push({ url: String(url), headers: (init?.headers ?? {}) as Record<string, string>, body: JSON.parse(String(init?.body)) });
    if (status !== 200) {
      return new Response(text, { status });
    }
    return new Response(JSON.stringify({ audioContent: MP3 }), { status: 200, headers: { "content-type": "application/json" } });
  };
  return impl as typeof fetch;
}

// ── SSML ───────────────────────────────────────────────────────────────────────

test("SSML — calm 은 prosody 없이, 다른 톤은 personas.json 힌트 값 그대로 문장 전체를 감싼다", () => {
  assert.equal(buildSsml("네, 한별시입니다.", "calm"), "<speak>네, 한별시입니다.</speak>");
  assert.equal(buildSsml("왜 안 되냐고요!", "shouting"), '<speak><prosody rate="115%" pitch="+5st" volume="+8dB">왜 안 되냐고요!</prosody></speak>');
  assert.equal(buildSsml("그냥 다 힘들어요", "weary"), '<speak><prosody rate="85%" pitch="-2st" volume="-4dB">그냥 다 힘들어요</prosody></speak>');
  assert.match(buildSsml("x", "tense"), /rate="105%" pitch="\+1st"/);
  assert.match(buildSsml("x", "raised"), /rate="110%" pitch="\+3st" volume="\+4dB"/);
});

test("SSML — XML 특수문자를 이스케이프한다(고객이 <, & 를 말해도 요청이 깨지지 않는다)", () => {
  assert.equal(escapeXml(`A & B <c> "d" 'e'`), "A &amp; B &lt;c&gt; &quot;d&quot; &apos;e&apos;");
  assert.equal(buildSsml("돈 & child <아동수당>", "calm"), "<speak>돈 &amp; child &lt;아동수당&gt;</speak>");
});

test("과금 문자 수는 태그·공백을 포함한 SSML 전체 코드포인트다(바이트가 아니다)", () => {
  const ssml = buildSsml("아동수당", "calm");
  assert.equal(billableChars(ssml), "<speak>".length + 4 + "</speak>".length);
  assert.ok(Buffer.byteLength(ssml, "utf-8") > billableChars(ssml), "한글은 바이트가 더 많다");
});

test("지문은 글자·음성·높이 중 하나라도 바뀌면 달라진다", () => {
  const base = { ssml: "<speak>a</speak>", voice: "ko-KR-Wavenet-A" as const, pitch: 0 };
  assert.equal(fingerprint(base), fingerprint({ ...base }));
  assert.notEqual(fingerprint(base), fingerprint({ ...base, ssml: "<speak>b</speak>" }));
  assert.notEqual(fingerprint(base), fingerprint({ ...base, voice: "ko-KR-Wavenet-B" }));
  assert.notEqual(fingerprint(base), fingerprint({ ...base, pitch: 1 }));
  assert.equal(cacheStem(3, "customer"), "03-customer");
});

// ── 음성 배분 ─────────────────────────────────────────────────────────────────

test("음성 배분 — 표의 페르소나는 고정, 상담원 셋은 서로 다른 목소리", () => {
  const agents = ["A01", "A02", "A03"].map((id) => pickVoice(id).voice);
  assert.equal(new Set(agents).size, 3);
  for (const choice of Object.values(PERSONA_VOICES)) {
    assert.ok(choice.voice in WAVENET_GENDER, choice.voice);
    assert.ok(choice.pitch >= -20 && choice.pitch <= 20);
  }
});

test("음성 배분 — 표에 없는 새 페르소나는 힌트의 남성/여성으로, 힌트도 없으면 기본값", () => {
  assert.equal(pickVoice("A04", { tts_voice_hint: "남성, 40대, 낮고 건조" }).voice, "ko-KR-Wavenet-B");
  assert.equal(pickVoice("C99", { tts_voice_hint: "여성, 30대" }).voice, "ko-KR-Wavenet-A");
  assert.equal(pickVoice("C99").voice, FALLBACK_VOICE);
  assert.equal(pickVoice(undefined).voice, FALLBACK_VOICE);
});

test("음성 배분 — personas.json 의 google_tts_voice 가 표보다 우선하고, 모르는 이름은 무시한다", () => {
  assert.equal(pickVoice("A01", { google_tts_voice: "ko-KR-Wavenet-D" }).voice, "ko-KR-Wavenet-D");
  assert.equal(pickVoice("A01", { google_tts_voice: "ko-KR-Chirp3-HD-Aoede" }).voice, PERSONA_VOICES["A01"]?.voice);
});

// ── 예산 가드 ─────────────────────────────────────────────────────────────────

test("예산 — 월 키만 더하고, 상한 직전은 통과·직후는 거절(호출 전 판정)", () => {
  const month = "2026-09";
  const ledger = { "2026-08": 800_000, [month]: 999_990 };
  assert.equal(usedInMonth(ledger, month), 999_990);
  assert.equal(decideSynthesis(ledger, 1_000_000, month, 10).ok, true);
  const over = decideSynthesis(ledger, 1_000_000, month, 11);
  assert.equal(over.ok, false);
  assert.match(over.ok ? "" : over.reason, /한도 초과/);
  assert.equal(decideSynthesis(charge({}, month, 5), 10, month, 5).ok, true);
  assert.equal(decideSynthesis(charge({}, month, 5), 10, month, 6).ok, false);
});

test("예산 — 달이 바뀌면 처음부터 센다, 상한 0 은 전부 막는다", () => {
  const ledger = { "2026-09": 900_000 };
  assert.equal(decideSynthesis(ledger, 900_000, "2026-10", 1).ok, true);
  assert.equal(decideSynthesis({}, 0, "2026-10", 1).ok, false);
  assert.equal(localMonth(new Date(2026, 8, 18)), "2026-09");
});

test("예산 — 환경변수: 비면 기본 900,000, 정수가 아니면 멈춘다", () => {
  assert.equal(capFromEnv({}), DEFAULT_MAX_CHARS_PER_MONTH);
  assert.equal(capFromEnv({ GOOGLE_TTS_MAX_CHARS_PER_MONTH: " 500000 " }), 500_000);
  assert.equal(capFromEnv({ GOOGLE_TTS_MAX_CHARS_PER_MONTH: "0" }), 0);
  assert.throws(() => capFromEnv({ GOOGLE_TTS_MAX_CHARS_PER_MONTH: "백만" }), /정수/);
  assert.throws(() => capFromEnv({ GOOGLE_TTS_MAX_CHARS_PER_MONTH: "-1" }), /정수/);
});

test("장부 파일 — 없으면 빈 장부, 쓰면 임시 파일 없이 하나만 남는다", async () => {
  const dir = await mkdtemp(join(tmpdir(), "tts-ledger-"));
  const file = new TtsLedgerFile(join(dir, "nested", "tts-usage.json"));
  assert.deepEqual(await file.read(), {});
  await file.write({ "2026-09": 42 });
  assert.deepEqual(await file.read(), { "2026-09": 42 });
  assert.deepEqual(await readdir(join(dir, "nested")), ["tts-usage.json"]);
});

// ── 합성 + 캐시 ──────────────────────────────────────────────────────────────

test("합성 — 첫 호출은 API 를 부르고 mp3·json 을 쓰고 장부에 더한다; 같은 입력의 두 번째는 호출 0", async () => {
  const dir = await mkdtemp(join(tmpdir(), "tts-cache-"));
  const calls: Array<{ url: string; headers: Record<string, string>; body: unknown }> = [];
  const store = new MemoryTtsLedger();
  const budget = new TtsBudget(store, 1000, () => new Date(2026, 8, 18));
  const req = { ssml: buildSsml("아동수당 신청하고 싶어요", "calm"), voice: "ko-KR-Wavenet-C" as const, pitch: 1 };

  const first = await synthesizeToCache({ req, dir, stem: "02-customer", apiKey: KEY, budget, fetchImpl: fakeFetch(calls) });
  assert.equal(first.cached, false);
  assert.equal(first.chars, billableChars(req.ssml));
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.url, TTS_ENDPOINT);
  assert.equal(calls[0]?.headers["x-goog-api-key"], KEY, "키는 헤더로 간다");
  assert.ok(!calls[0]?.url.includes(KEY), "키가 URL 에 없다");
  assert.deepEqual(calls[0]?.body, {
    input: { ssml: req.ssml },
    voice: { languageCode: "ko-KR", name: "ko-KR-Wavenet-C" },
    audioConfig: { audioEncoding: "MP3", pitch: 1 },
  });
  assert.equal((await readFile(join(dir, "02-customer.mp3"))).toString("base64"), MP3);
  const meta = JSON.parse(await readFile(join(dir, "02-customer.json"), "utf-8")) as { chars: number; fingerprint: string };
  assert.equal(meta.chars, first.chars);
  assert.equal(meta.fingerprint, fingerprint(req));
  assert.deepEqual(store.ledger, { "2026-09": first.chars });

  const second = await synthesizeToCache({ req, dir, stem: "02-customer", apiKey: "", budget, fetchImpl: fakeFetch(calls) });
  assert.equal(second.cached, true);
  assert.equal(second.chars, 0);
  assert.equal(calls.length, 1, "캐시 히트는 API 를 부르지 않고 키도 필요 없다");
  assert.deepEqual(store.ledger, { "2026-09": first.chars }, "캐시 히트는 장부에 더하지 않는다");
});

test("합성 — 입력이 바뀌면 다시 부르고, pitch 0 은 audioConfig 에 싣지 않는다", async () => {
  const dir = await mkdtemp(join(tmpdir(), "tts-cache-"));
  const calls: Array<{ url: string; headers: Record<string, string>; body: unknown }> = [];
  const budget = new TtsBudget(new MemoryTtsLedger(), 1000);
  const a = { ssml: buildSsml("네", "calm"), voice: "ko-KR-Wavenet-A" as const, pitch: 0 };
  await synthesizeToCache({ req: a, dir, stem: "01-agent", apiKey: KEY, budget, fetchImpl: fakeFetch(calls) });
  await synthesizeToCache({ req: { ...a, ssml: buildSsml("네", "tense") }, dir, stem: "01-agent", apiKey: KEY, budget, fetchImpl: fakeFetch(calls) });
  assert.equal(calls.length, 2);
  assert.deepEqual((calls[0]?.body as { audioConfig: unknown }).audioConfig, { audioEncoding: "MP3" });
});

test("합성 — 예산이 모자라면 API 를 부르지 않고 TtsBudgetExceeded, 키가 없고 캐시도 없으면 명확히 실패", async () => {
  const dir = await mkdtemp(join(tmpdir(), "tts-cache-"));
  const calls: Array<{ url: string; headers: Record<string, string>; body: unknown }> = [];
  const store = new MemoryTtsLedger({ [localMonth(new Date())]: 990 });
  const budget = new TtsBudget(store, 1000);
  const req = { ssml: buildSsml("이건 예산을 넘기는 긴 문장입니다", "calm"), voice: "ko-KR-Wavenet-A" as const, pitch: 0 };
  await assert.rejects(
    synthesizeToCache({ req, dir, stem: "05-customer", apiKey: KEY, budget, fetchImpl: fakeFetch(calls) }),
    (error: unknown) => error instanceof TtsBudgetExceeded && /한도 초과/.test(error.message),
  );
  assert.equal(calls.length, 0);
  assert.equal(store.ledger[localMonth(new Date())], 990, "거절된 요청은 장부에 더하지 않는다");

  await assert.rejects(
    synthesizeToCache({ req, dir, stem: "05-customer", apiKey: "", budget: new TtsBudget(new MemoryTtsLedger(), 1000), fetchImpl: fakeFetch(calls) }),
    /GOOGLE_TTS_API_KEY 가 비어 있고 캐시도 없다/,
  );
  assert.equal(calls.length, 0);
});

test("합성 — 구글 오류 본문에 키가 섞여 돌아와도 메시지에서 지운다, 5,000 바이트 초과는 부르기 전에 막는다", async () => {
  const dir = await mkdtemp(join(tmpdir(), "tts-cache-"));
  const calls: Array<{ url: string; headers: Record<string, string>; body: unknown }> = [];
  const budget = new TtsBudget(new MemoryTtsLedger(), 1_000_000);
  const req = { ssml: buildSsml("네", "calm"), voice: "ko-KR-Wavenet-A" as const, pitch: 0 };
  await assert.rejects(
    synthesizeToCache({ req, dir, stem: "01-agent", apiKey: KEY, budget, fetchImpl: fakeFetch(calls, 403, `API key ${KEY} not valid`) }),
    (error: unknown) => error instanceof Error && /HTTP 403/.test(error.message) && !error.message.includes(KEY) && error.message.includes("<redacted>"),
  );
  assert.equal(redact("no secret here", ""), "no secret here");

  const huge = { ...req, ssml: buildSsml("가".repeat(MAX_INPUT_BYTES), "calm") };
  await assert.rejects(synthesizeToCache({ req: huge, dir, stem: "01-agent", apiKey: KEY, budget, fetchImpl: fakeFetch(calls) }), /5000 바이트/);
  assert.equal(calls.length, 1, "403 한 번만 불렀고 초과 요청은 안 불렀다");
});

test("플레이어 — afplay 우선(배속은 -r), 없으면 ffplay, 둘 다 없으면 null", () => {
  const afplay = findPlayer((c) => c === "afplay");
  assert.deepEqual(afplay?.args("x.mp3"), ["x.mp3"]);
  assert.deepEqual(afplay?.args("x.mp3", 2), ["-r", "2", "x.mp3"]);
  assert.equal(findPlayer((c) => c === "ffplay")?.command, "ffplay");
  assert.equal(findPlayer(() => false), null);
});
