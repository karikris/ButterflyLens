/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BUTTERFLYLENS_MONITORING_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
