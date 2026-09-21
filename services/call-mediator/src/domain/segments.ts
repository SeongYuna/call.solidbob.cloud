// Requirement: A-1, A-2, 7.3절 전사 이벤트
/**
 * 발화 번호(`segment_id`)와 발화 종료 시각(`utterance_end_ms`)을 정하는 규칙.
 *
 * - `segment_id` 는 **통화 안에서** 유일하다. 화자가 둘(채널 분리)이어도 번호는 하나의 줄에서
 *   나온다 — `transcript_segment` 의 키가 `(call_id, segment_id)` 이기 때문이다.
 * - interim 은 같은 번호를 이어 쓰고(대시보드가 그 번호로 **교체**한다, [7.3절] 자막 렌더링),
 *   final 이 오면 번호를 닫는다. 다음 결과는 새 번호다.
 * - 시각은 **통화 시작 기준 ms** 다. STT 어댑터가 스트림 교대를 감춰 채널 첫 오디오부터
 *   이어지는 시각을 주므로, 여기서는 채널이 열린 시각만 더한다.
 */

export class SegmentCounter {
  private last = 0;

  next(): number {
    this.last += 1;
    return this.last;
  }
}

/** 채널(화자 하나) 안에서 지금 열려 있는 발화 번호를 들고 있다. */
export class OpenSegment {
  private readonly counter: SegmentCounter;
  private current: number | null = null;

  constructor(counter: SegmentCounter) {
    this.counter = counter;
  }

  /** 결과 하나에 붙일 번호. final 이면 이 번호를 닫는다. */
  idFor(isFinal: boolean): number {
    if (this.current === null) {
      this.current = this.counter.next();
    }
    const id = this.current;
    if (isFinal) {
      this.current = null;
    }
    return id;
  }
}

/**
 * @param channelStartMs 통화 시작 → 이 채널이 열린 시각 (벽시계 차이)
 * @param audioEndMs     채널 첫 오디오 기준 발화 종료 시각 (STT 어댑터가 교대를 감춘 값)
 */
export function utteranceEndMs(channelStartMs: number, audioEndMs: number): number {
  return Math.max(0, Math.round(channelStartMs + audioEndMs));
}
