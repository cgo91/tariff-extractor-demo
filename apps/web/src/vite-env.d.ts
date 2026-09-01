/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Overrides the API base URL; defaults to the /api dev proxy. */
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
