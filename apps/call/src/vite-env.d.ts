/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GATEWAY_WS_URL?: string;
  readonly VITE_CORE_API_URL?: string;
  /** "고객과 전화하기" 마이크 데모(AgentCallBox, 팀 전용)가 쓰는 게이트웨이 기본 주소. */
  readonly VITE_GATEWAY_DEMO_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
