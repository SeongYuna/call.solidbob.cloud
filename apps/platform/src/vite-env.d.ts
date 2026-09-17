/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** services/call-mediator 주소. 예: wss://server.solidbob.cloud/call-mediator — 팀 전용 통화 데모(Hero)가 쓴다. */
  readonly VITE_CALL_MEDIATOR_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
