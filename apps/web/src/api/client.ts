/**
 * Thin HTTP client for the API.
 *
 * Responsibilities: prefix the base URL, attach the bearer token, and turn any
 * non-2xx response into an `ApiError` carrying the backend's own message so the
 * UI never has to invent one.
 */

import type { ApiErrorBody } from '@/types/api'

// Vite proxies /api to the backend during development (see vite.config.ts).
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }

  /** True when the session is gone and the user must sign in again. */
  get isUnauthorized(): boolean {
    return this.status === 401
  }
}

/** Reads the token the AuthProvider stored, so requests survive a reload. */
type TokenReader = () => string | null

let readToken: TokenReader = () => null

/** Registers where the client should look for the current access token. */
export function setTokenReader(reader: TokenReader): void {
  readToken = reader
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  /** Skip the Authorization header (used by the login call). */
  anonymous?: boolean
  signal?: AbortSignal
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = 'http_error'
  let message = `La solicitud falló (${response.status})`

  try {
    const body = (await response.json()) as Partial<ApiErrorBody> & {
      detail?: unknown
    }
    if (typeof body.message === 'string') {
      message = body.message
    } else if (typeof body.detail === 'string') {
      message = body.detail
    } else if (Array.isArray(body.detail)) {
      // FastAPI validation errors arrive as a list of issues.
      message = 'Revisa los datos enviados: hay campos inválidos.'
    }
    if (typeof body.code === 'string') {
      code = body.code
    }
  } catch {
    // A non-JSON body (a proxy error page, for instance) keeps the default.
  }

  return new ApiError(response.status, code, message)
}

/** Uploads a file as multipart/form-data and returns the parsed body. */
export async function upload<T>(path: string, file: File): Promise<T> {
  const form = new FormData()
  form.append('file', file)

  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = readToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  // Content-Type is deliberately omitted: the browser must set it so the
  // multipart boundary is included.
  const response = await fetch(`${BASE_URL}${path}`, { method: 'POST', headers, body: form })

  if (!response.ok) {
    throw await toApiError(response)
  }
  return (await response.json()) as T
}

/** Fetches a binary resource as an object URL the browser can render. */
export async function fetchBlobUrl(path: string): Promise<string> {
  const headers: Record<string, string> = {}
  const token = readToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${BASE_URL}${path}`, { headers })
  if (!response.ok) {
    throw await toApiError(response)
  }
  return URL.createObjectURL(await response.blob())
}

/** Performs a JSON request and returns the parsed body. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, anonymous = false, signal } = options

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (!anonymous) {
    const token = readToken()
    if (token) {
      headers.Authorization = `Bearer ${token}`
    }
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })

  if (!response.ok) {
    throw await toApiError(response)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
