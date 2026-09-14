// Requirement: A-3, 7.3절 전사 이벤트
/**
 * 채널 하나의 전사 결과를 서버에 **순서대로, 하나씩** 보내는 줄.
 *
 * 구글은 발화 하나에 interim 을 수십~수백 개 보낸다(V4 실측: 20초 발화에 199건). 전부 서버에
 * 보내면 요청이 쌓여 자막이 점점 늦어진다. 대시보드는 같은 `segment_id` 의 최신 것만 쓰므로
 * (7.3절 자막 렌더링) **아직 보내지 않은 interim 은 같은 발화의 더 새 결과로 갈아 끼운다.**
 *
 * final 은 갈아 끼워지지 않는다 — 저장·트리거가 final 에만 걸려 있다. 그리고 순서가 뒤집히지
 * 않는다: 먼저 온 final 의 응답보다 나중 interim 이 먼저 화면에 가는 일이 없다.
 */

export interface QueueItem {
  segmentId: number;
  isFinal: boolean;
}

export class CoalescingQueue<T extends QueueItem> {
  private readonly items: T[] = [];
  private readonly handler: (item: T) => Promise<void>;
  private running = false;
  private idleWaiters: Array<() => void> = [];

  constructor(handler: (item: T) => Promise<void>) {
    this.handler = handler;
  }

  push(item: T): void {
    const last = this.items[this.items.length - 1];
    if (last !== undefined && !last.isFinal && last.segmentId === item.segmentId) {
      // 대기 중인 interim 을 같은 발화의 새 결과(interim 이든 final 이든)로 바꾼다.
      this.items[this.items.length - 1] = item;
    } else {
      this.items.push(item);
    }
    void this.drain();
  }

  /** 대기 중인 것이 없고 처리 중인 것도 없으면 풀린다. */
  whenIdle(): Promise<void> {
    if (!this.running && this.items.length === 0) {
      return Promise.resolve();
    }
    return new Promise((resolve) => this.idleWaiters.push(resolve));
  }

  get pending(): number {
    return this.items.length;
  }

  private async drain(): Promise<void> {
    if (this.running) {
      return;
    }
    this.running = true;
    try {
      for (let item = this.items.shift(); item !== undefined; item = this.items.shift()) {
        try {
          await this.handler(item);
        } catch {
          // 처리기가 자기 실패를 기록한다. 한 건 실패로 줄이 멈추면 뒤 자막이 전부 사라진다.
        }
      }
    } finally {
      this.running = false;
      const waiters = this.idleWaiters;
      this.idleWaiters = [];
      for (const resolve of waiters) {
        resolve();
      }
    }
  }
}
