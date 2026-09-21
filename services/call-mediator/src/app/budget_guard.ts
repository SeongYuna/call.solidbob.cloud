// Requirement: COST-1
/**
 * STT 사용량 2차 가드 — 1차는 GCP 콘솔 쿼터(하드 리밋)다([w1-stt-billing-quota]).
 *
 * `.claude/rules/rfp-harness.md` COST-1 이 정한 두 동작을 둘 다 한다.
 * ① 캡을 넘겼으면 **새 스트림을 열지 않는다** — `decideOpen`
 * ② 열려 있는 스트림도 캡에 닿으면 **거기서 끊는다** — `consume`.
 *    ①만 있으면 스트림 하나가 캡을 한참 넘겨 과금된다. 스트림은 끝을 미리 모른다.
 *
 * 모든 채널이 가드 하나를 나눠 쓴다(캡은 머신 전체 한도다). 장부 파일은 매 청크마다 쓰지 않고
 * `flushEverySeconds` 마다 한 번 쓴다 — 초당 수십 번 파일을 쓰지 않으려는 것이다. 그 사이의
 * 사용량은 메모리(`pending`)에 있고, 판정은 늘 `장부 + pending` 으로 한다.
 */
import {
  capsConfigured,
  charged,
  decideOpen,
  localDay,
  remainingSeconds,
  type Caps,
  type Ledger,
  type OpenDecision,
} from "../domain/budget.ts";
import type { LedgerStore, Logger } from "./ports.ts";

export interface BudgetSnapshot {
  capsConfigured: boolean;
  capDay: number;
  capMonth: number;
  usedTodaySeconds: number;
  usedMonthSeconds: number;
}

export class BudgetGuard {
  private readonly store: LedgerStore;
  private readonly caps: Caps;
  private readonly now: () => Date;
  private readonly log: Logger;
  private readonly flushEverySeconds: number;
  private baseline: Ledger = {};
  private pending = 0;
  private flushing: Promise<void> = Promise.resolve();
  /** 마지막 장부 쓰기가 실패했다. 풀릴 때까지 새 스트림을 열지 않는다(a5 세션 검토, 2026-09-11). */
  private writeFailed = false;

  constructor(store: LedgerStore, caps: Caps, now: () => Date, log: Logger, flushEverySeconds = 5) {
    this.store = store;
    this.caps = caps;
    this.now = now;
    this.log = log;
    this.flushEverySeconds = flushEverySeconds;
  }

  /**
   * 장부를 다시 읽는다. 기동할 때 부른다 — 안 그러면 첫 채널이 열리기 전까지 `/health` 가
   * 배치 스크립트·이전 실행이 쓴 사용량을 0 으로 보고한다(2026-09-11 실측).
   */
  async refresh(): Promise<void> {
    try {
      this.baseline = await this.store.read();
    } catch {
      this.log.warn("STT 사용량 장부를 읽지 못했다 — 채널을 열 때 다시 읽고, 못 읽으면 거절한다");
    }
  }

  async decideOpen(): Promise<OpenDecision> {
    try {
      this.baseline = await this.store.read();
    } catch {
      // 장부를 못 읽으면 얼마나 썼는지 모른다 — 모르면 막는다.
      return { ok: false, reason: "STT 사용량 장부를 읽지 못했다 — 스트림을 열지 않는다(COST-1)" };
    }
    if (this.writeFailed) {
      // 쓴 초를 장부에 못 남기고 있다 — 이 상태로 새로 열면 재시작 뒤 그만큼이 사라진다. 먼저 한 번 더 써 본다.
      await this.flush();
      if (this.writeFailed) {
        return { ok: false, reason: "STT 사용량 장부에 쓰지 못하고 있다 — 새 스트림을 열지 않는다(COST-1)" };
      }
    }
    const day = localDay(this.now());
    return decideOpen(charged(this.baseline, day, this.pending), this.caps, day);
  }

  /**
   * 오디오를 STT 로 보내기 **전에** 부른다. false 면 캡에 닿았다 — 보내지 말고 채널을 닫는다.
   * true 면 그 초를 사용량에 올렸다.
   */
  consume(seconds: number): boolean {
    if (!capsConfigured(this.caps)) {
      return false;
    }
    const day = localDay(this.now());
    const left = remainingSeconds(charged(this.baseline, day, this.pending), this.caps, day);
    if (seconds > left) {
      return false;
    }
    this.pending += seconds;
    if (this.pending >= this.flushEverySeconds) {
      void this.flush();
    }
    return true;
  }

  /** 메모리에 쌓인 사용량을 장부에 쓴다. 채널이 닫힐 때도 부른다. */
  flush(): Promise<void> {
    this.flushing = this.flushing.then(async () => {
      const seconds = this.pending;
      if (seconds <= 0) {
        return;
      }
      this.pending = 0;
      try {
        this.baseline = await this.store.add(localDay(this.now()), seconds);
        this.writeFailed = false;
      } catch {
        // 못 썼으면 되돌려 둔다 — 버리면 사용량이 줄어든 것처럼 보인다. 열린 채널은 메모리로 계속 캡을 지킨다.
        this.pending += seconds;
        this.writeFailed = true;
        this.log.warn(`STT 사용량 장부 쓰기 실패 — ${seconds.toFixed(1)}초를 메모리에 두고, 새 스트림은 막는다`);
      }
    });
    return this.flushing;
  }

  snapshot(): BudgetSnapshot {
    const day = localDay(this.now());
    const ledger = charged(this.baseline, day, this.pending);
    let usedMonth = 0;
    for (const [key, value] of Object.entries(ledger)) {
      if (key.startsWith(day.slice(0, 7))) {
        usedMonth += value;
      }
    }
    return {
      capsConfigured: capsConfigured(this.caps),
      capDay: this.caps.perDay,
      capMonth: this.caps.perMonth,
      usedTodaySeconds: Math.round((ledger[day] ?? 0) * 10) / 10,
      usedMonthSeconds: Math.round(usedMonth * 10) / 10,
    };
  }
}
