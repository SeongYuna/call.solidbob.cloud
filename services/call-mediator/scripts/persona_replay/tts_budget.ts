// Requirement: COST-1
/**
 * Google TTS 문자 수 **2차 가드** — STT 의 `src/domain/budget.ts`(COST-1)와 같은 2단 구조다.
 * 1차는 GCP 콘솔의 할당량·예산 알림, 2차가 여기다: **호출하기 전에** 장부 + 이번 요청 문자 수가 상한을 넘으면 부르지 않는다.
 *
 * 장부 `data/processed/tts-usage.json` — `{"YYYY-MM": 청구 문자 수}`. 구글은 **입력 전체 문자 수**로 과금한다 — 공백·줄바꿈·
 * SSML 태그(`<mark>` 제외)까지 센다(https://cloud.google.com/text-to-speech/pricing 「Price is calculated per character」,
 * 2026-09-18 확인). 그래서 장부에 더하는 값은 발화 글자 수가 아니라 **SSML 전체** 길이다(`google_tts.ts` `billableChars`).
 *
 * `src/adapters/ledger_file.ts` 를 import 하지 않고 작게 다시 썼다 — `src/` 를 건드리면 콜 미디에이터 이미지 태그를 올려야 한다.
 * STT 장부(`stt-usage.json`, 초 단위)와는 **다른 파일**이다 — 단위가 다르다.
 *
 * 상한 기본값 900,000 자/월. 공식 무료 한도는 WaveNet·Standard 합산 400만 자/월(같은 SKU)이지만, 같은 프로젝트의 다른
 * 사용(관리자 실험 등)을 모르니 넉넉히 아래에 둔다. `GOOGLE_TTS_MAX_CHARS_PER_MONTH` 로 바꾼다 — `0` 은 「전부 막음」이다.
 */
import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

export type TtsLedger = Record<string, number>;

export const DEFAULT_MAX_CHARS_PER_MONTH = 900_000;
export const ENV_CAP = "GOOGLE_TTS_MAX_CHARS_PER_MONTH";

export type SynthesisDecision = { ok: true; remainingChars: number } | { ok: false; reason: string };

export interface TtsLedgerStore {
  read(): Promise<TtsLedger>;
  write(ledger: TtsLedger): Promise<void>;
}

/** 로컬 시각 기준 `YYYY-MM`. 구글 무료 한도도 달력 월 단위다. */
export function localMonth(now: Date): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function usedInMonth(ledger: TtsLedger, month: string): number {
  const used = ledger[month];
  return typeof used === "number" && Number.isFinite(used) && used > 0 ? used : 0;
}

/** 환경변수 → 상한. 비어 있으면 기본값, 숫자가 아니거나 음수면 멈춘다(조용히 기본값으로 가지 않는다). */
export function capFromEnv(env: Record<string, string | undefined>): number {
  const raw = (env[ENV_CAP] ?? "").trim();
  if (raw === "") {
    return DEFAULT_MAX_CHARS_PER_MONTH;
  }
  const cap = Number(raw);
  if (!Number.isInteger(cap) || cap < 0) {
    throw new Error(`${ENV_CAP}=${raw} — 0 이상의 정수여야 한다(0 은 전부 막음)`);
  }
  return cap;
}

export function decideSynthesis(ledger: TtsLedger, cap: number, month: string, chars: number): SynthesisDecision {
  const used = usedInMonth(ledger, month);
  if (used + chars > cap) {
    return {
      ok: false,
      reason: `Google TTS 월 문자 한도 초과 — 이번 달 ${used.toLocaleString()} + 요청 ${chars.toLocaleString()} > 상한 ${cap.toLocaleString()} (${ENV_CAP})`,
    };
  }
  return { ok: true, remainingChars: cap - used - chars };
}

export function charge(ledger: TtsLedger, month: string, chars: number): TtsLedger {
  return { ...ledger, [month]: usedInMonth(ledger, month) + chars };
}

/** 임시 파일에 쓰고 이름을 바꾼다 — 쓰다 죽어도 반쯤 쓴 JSON 이 남지 않게. */
export class TtsLedgerFile implements TtsLedgerStore {
  private readonly path: string;

  constructor(path: string) {
    this.path = path;
  }

  async read(): Promise<TtsLedger> {
    let text: string;
    try {
      text = await readFile(this.path, "utf-8");
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") {
        return {};
      }
      throw error;
    }
    const parsed: unknown = JSON.parse(text);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`${this.path} 가 장부 형식({"YYYY-MM": 문자 수})이 아니다`);
    }
    return parsed as TtsLedger;
  }

  async write(ledger: TtsLedger): Promise<void> {
    await mkdir(dirname(this.path), { recursive: true });
    const tmp = `${this.path}.${process.pid}.tmp`;
    await writeFile(tmp, `${JSON.stringify(ledger, null, 1)}\n`, "utf-8");
    await rename(tmp, this.path);
  }
}

export class MemoryTtsLedger implements TtsLedgerStore {
  ledger: TtsLedger;

  constructor(initial: TtsLedger = {}) {
    this.ledger = { ...initial };
  }

  read(): Promise<TtsLedger> {
    return Promise.resolve({ ...this.ledger });
  }

  write(ledger: TtsLedger): Promise<void> {
    this.ledger = { ...ledger };
    return Promise.resolve();
  }
}

/** 호출마다 장부를 다시 읽는다 — 한 번의 재생·프리페치는 기껏 수백 요청이라 파일 몇 번 읽는 값이 싸다. */
export class TtsBudget {
  private readonly store: TtsLedgerStore;
  private readonly cap: number;
  private readonly now: () => Date;

  constructor(store: TtsLedgerStore, cap: number, now: () => Date = () => new Date()) {
    this.store = store;
    this.cap = cap;
    this.now = now;
  }

  async decide(chars: number): Promise<SynthesisDecision> {
    return decideSynthesis(await this.store.read(), this.cap, localMonth(this.now()), chars);
  }

  /** 성공한 요청만 더한다. 거절된 요청·캐시 히트는 여기 오지 않는다. */
  async charge(chars: number): Promise<void> {
    await this.store.write(charge(await this.store.read(), localMonth(this.now()), chars));
  }

  async used(): Promise<{ month: string; used: number; cap: number }> {
    const month = localMonth(this.now());
    return { month, used: usedInMonth(await this.store.read(), month), cap: this.cap };
  }
}
