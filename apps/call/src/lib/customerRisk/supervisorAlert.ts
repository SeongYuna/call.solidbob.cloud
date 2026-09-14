export type SupervisorAlertType = "abuse" | "distress";

export interface SupervisorAlert {
  type: SupervisorAlertType;
  matchedText: string;
  callId: string;
  timestamp: number;
}

/** 전송 목업. 웹소켓·API가 생기면 이 시그니처로 갈아끼운다. */
export function logSupervisorAlert(alert: SupervisorAlert): void {
  console.info("[C-6] supervisor alert (mock)", alert);
}
