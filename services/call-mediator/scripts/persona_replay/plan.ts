// Requirement: A-1, A-3, D-5
/**
 * 합성 통화 대본(`scripts/persona_sim/`)을 **말하는 속도로** 흘릴 계획을 세운다 — 순수 함수만 둔다(테스트 대상).
 *
 * 대본에는 발화 시각이 없다. 사람이 말하는 것처럼 보이게 하려면 ① 한 턴을 몇 ms 동안 말하는지 ② 그 사이 부분 결과
 * (`is_final: false`)를 언제 무엇으로 보내는지를 여기서 정한다. 실제 STT 의 부분 결과처럼 **앞에서부터 어절 단위로
 * 늘어나는 글자**를 보내고, 마지막에 전체를 확정으로 보낸다.
 *
 * ⚠ 여기서 나온 시각은 **지어낸 값**이다. 이 재생으로 트리거 지연(B-1 p95)을 재면 안 된다(절대 원칙 10) —
 * 통화 기록 엔진 이름이 `synthetic-script` 로 남는 이유다.
 */

export type Speaker = "agent" | "customer";
export type Tone = "calm" | "tense" | "raised" | "shouting" | "weary";

export interface ScriptTurn {
  seq: number;
  speaker: Speaker;
  text: string;
  tone: Tone;
}

export interface TurnPlan {
  /** 이 턴을 말하는 데 드는 시간(ms). 확정 결과는 이 시각에 보낸다. */
  durationMs: number;
  /** 턴 시작 기준 부분 결과. 시각 오름차순, 마지막 것도 전체 글자보다 짧다. */
  interims: Array<{ offsetMs: number; text: string }>;
}

/** 한 글자(음절)당 ms — 한국어 낭독이 대략 초당 6~7음절이다. 톤이 오르면 빨라지고 가라앉으면 느려진다. */
const MS_PER_CHAR: Record<Tone, number> = { calm: 150, tense: 135, raised: 125, shouting: 115, weary: 200 };
/** macOS `say -r`(분당 단어). 목소리 크기는 `say` 명령줄로 못 바꾼다 — 운율 흉내는 속도까지다. */
const SAY_RATE: Record<Tone, number> = { calm: 185, tense: 205, raised: 220, shouting: 235, weary: 145 };
const MIN_TURN_MS = 700;
/** 부분 결과를 몇 어절마다 보내나. 실제 스트리밍 STT 도 한 어절씩보다는 뭉쳐서 온다. */
const WORDS_PER_INTERIM = 2;

export const TONES: readonly Tone[] = ["calm", "tense", "raised", "shouting", "weary"];

export function sayRate(tone: Tone): number {
  return SAY_RATE[tone];
}

export function planTurn(turn: ScriptTurn, speed = 1): TurnPlan {
  if (!(speed > 0)) {
    throw new Error("speed 는 0 보다 커야 한다");
  }
  const syllables = [...turn.text.replace(/\s+/g, "")].length;
  const durationMs = Math.round(Math.max(MIN_TURN_MS, syllables * MS_PER_CHAR[turn.tone]) / speed);

  const words = turn.text.trim().split(/\s+/);
  const prefixes: string[] = [];
  for (let n = WORDS_PER_INTERIM; n < words.length; n += WORDS_PER_INTERIM) {
    prefixes.push(words.slice(0, n).join(" "));
  }
  const totalChars = turn.text.length;
  const interims = prefixes.map((text) => ({
    // 앞 글자 비율만큼 시간이 지났을 때 보낸다 — 긴 어절이 앞에 있으면 그만큼 늦게 뜬다.
    offsetMs: Math.round((durationMs * text.length) / totalChars),
    text,
  }));
  return { durationMs, interims };
}

/** 턴 사이 쉬는 시간(ms). 화자가 바뀌면 조금 더 쉰다 — 상대 말을 듣고 답하는 틈이다. */
export function gapBefore(previous: ScriptTurn | undefined, turn: ScriptTurn, speed = 1): number {
  if (previous === undefined) {
    return 0;
  }
  return Math.round((previous.speaker === turn.speaker ? 250 : 550) / speed);
}

/** 대본 JSON 에서 재생에 필요한 턴만 꺼낸다. 형식이 틀리면 어느 턴인지 밝히고 멈춘다. */
export function readTurns(script: unknown): ScriptTurn[] {
  const turns = (script as { turns?: unknown } | null)?.turns;
  if (!Array.isArray(turns) || turns.length === 0) {
    throw new Error("대본에 turns 가 없다");
  }
  return turns.map((raw, index) => {
    const t = raw as Partial<ScriptTurn>;
    const where = `turns[${index}]`;
    if (t.speaker !== "agent" && t.speaker !== "customer") {
      throw new Error(`${where}.speaker 는 agent 또는 customer 다`);
    }
    if (typeof t.text !== "string" || t.text.trim().length === 0) {
      throw new Error(`${where}.text 가 비었다`);
    }
    const tone = TONES.includes(t.tone as Tone) ? (t.tone as Tone) : "calm";
    return { seq: typeof t.seq === "number" ? t.seq : index + 1, speaker: t.speaker, text: t.text, tone };
  });
}
