// Requirement: A-3, C-5
/**
 * 재생기가 보낸 **확정 자막**이 `/ws` 로 되돌아왔는지 센다 — 마지막 턴을 확인하기 전에 생산자 연결을 닫지 않으려고.
 *
 * 2026-09-22 운영 SYN-010 에서 마지막 턴(상담원 인사)이 저장되지 않았다(4/5, `--watch` 자막도 4개). 전에는 마지막 확정을
 * 보내자마자 `{"type":"end"}` 를 보내고 **10초 경주 + 3초** 뒤에 닫았다 — 그 사이 마지막 확정이 돌아왔는지는 아무도 보지 않았다.
 * 이제는 「화자별로 보낸 확정 수 == `/ws` 로 돌아온 확정 수」가 될 때까지 기다리고, 상한을 넘기면 **경고를 찍는다**(조용히 닫지 않는다).
 *
 * 되돌아온 본문은 마스킹본이라 원문과 대조할 수 없다 — 그래서 **글자가 아니라 개수**로 센다. 화자별로 세는 이유: 두 채널은
 * 서로 다른 줄(콜 미디에이터 `CoalescingQueue`)로 가서 도착 순서가 보장되지 않는다. 같은 `segment_id` 는 한 번만 센다.
 */
import type { Speaker } from "./plan.ts";

export type EchoCount = Record<Speaker, number>;

export interface EchoResult {
  ok: boolean;
  /** 화자별로 아직 돌아오지 않은 확정 수 */
  missing: EchoCount;
  waitedMs: number;
}

export class FinalEchoTracker {
  private readonly sent: EchoCount = { agent: 0, customer: 0 };
  private readonly seen: Record<Speaker, Set<number>> = { agent: new Set(), customer: new Set() };
  private waiters: Array<() => void> = [];

  /** 확정 하나를 생산자 소켓으로 보냈다. */
  noteSent(speaker: Speaker): void {
    this.sent[speaker] += 1;
  }

  /** `/ws` 로 확정 자막 하나가 돌아왔다. */
  noteEcho(speaker: Speaker, segmentId: number): void {
    this.seen[speaker].add(segmentId);
    if (this.complete()) {
      for (const resolve of this.waiters.splice(0)) {
        resolve();
      }
    }
  }

  missing(): EchoCount {
    return {
      agent: Math.max(0, this.sent.agent - this.seen.agent.size),
      customer: Math.max(0, this.sent.customer - this.seen.customer.size),
    };
  }

  complete(): boolean {
    const m = this.missing();
    return m.agent === 0 && m.customer === 0;
  }

  /** 보낸 확정이 전부 돌아오면 풀린다. `timeoutMs` 를 넘기면 `ok:false` 로 풀린다 — 예외를 던지지 않는다. */
  async whenAllEchoed(timeoutMs: number, now: () => number = Date.now): Promise<EchoResult> {
    const started = now();
    if (!this.complete()) {
      let timer: NodeJS.Timeout | undefined;
      await Promise.race([
        new Promise<void>((resolve) => this.waiters.push(resolve)),
        new Promise<void>((resolve) => {
          timer = setTimeout(resolve, Math.max(0, timeoutMs));
        }),
      ]);
      clearTimeout(timer);
    }
    return { ok: this.complete(), missing: this.missing(), waitedMs: now() - started };
  }
}

/** 경고 한 줄 — 무엇이 몇 개 안 돌아왔는지. 원문은 싣지 않는다. */
export function describeMissing(result: EchoResult): string {
  const parts = [
    result.missing.agent > 0 ? `상담원 ${result.missing.agent}` : "",
    result.missing.customer > 0 ? `고객 ${result.missing.customer}` : "",
  ].filter(Boolean);
  return `확정 자막 ${parts.join(" · ")}건이 ${Math.round(result.waitedMs / 1000)}초 안에 /ws 로 돌아오지 않았다`;
}
