/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GATEWAY_WS_URL?: string;
  readonly VITE_CORE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
