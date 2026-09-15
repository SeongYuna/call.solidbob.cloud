/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** services/gateway 주소. 예: wss://server.solidbob.cloud/gateway — 팀 전용 통화 데모(Hero)가 쓴다. */
  readonly VITE_GATEWAY_WS_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
