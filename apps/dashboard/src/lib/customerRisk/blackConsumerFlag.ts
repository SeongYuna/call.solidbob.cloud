/**
 * C-6 확장 — 상담원이 통화 종료 시 수동으로 내리는 판단이다. 자동 탐지가 아니다(부록 A-2).
 * 전송 목업. 관리자 알림 API(`services/gateway`)가 생기면 이 시그니처로 갈아끼운다.
 */
export interface BlackConsumerFlag {
  call_id: string;
  flagged_at: number;
}

export function reportBlackConsumer(flag: BlackConsumerFlag): void {
  console.info("[black-consumer] supervisor notified (mock)", flag);
}
