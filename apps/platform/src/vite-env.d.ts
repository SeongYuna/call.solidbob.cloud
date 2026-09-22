/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** services/call-mediator 주소. 예: wss://server.solidbob.cloud/call-mediator — 팀 전용 통화 데모(Hero)가 쓴다. */
  readonly VITE_CALL_MEDIATOR_WS_URL?: string;
  /**
   * 상담원 대시보드(apps/call) 주소 — "상담원 링크 복사" 버튼이 여기에 `?call_id=`·
   * `?call_token=`을 붙여 링크를 만든다. 비밀값이 아니라 공개 도메인이라 안 정해도
   * 기본값(`https://call.solidbob.cloud`)으로 동작한다.
   */
  readonly VITE_CALL_APP_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
