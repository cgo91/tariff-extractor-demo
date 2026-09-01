/** Typed wrappers around the API routes, grouped by resource. */

import { fetchBlobUrl, request, upload } from '@/api/client'
import type {
  AppConfig,
  CatalogSearchResponse,
  CurrentUser,
  LoginResponse,
  Operation,
  OperationDetails,
  OperationSummary,
} from '@/types/api'

export const authApi = {
  /** Exchanges credentials for an access token. */
  login(email: string, password: string): Promise<LoginResponse> {
    return request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
      anonymous: true,
    })
  },

  /** Confirms a stored token is still valid and returns its owner. */
  me(): Promise<CurrentUser> {
    return request<CurrentUser>('/auth/me')
  },
}

export const catalogApi = {
  /** Searches the tariff catalog by free text. */
  search(query: string, signal?: AbortSignal): Promise<CatalogSearchResponse> {
    const params = new URLSearchParams({ q: query })
    return request<CatalogSearchResponse>(`/catalog/search?${params}`, { signal })
  },
}

export const operationsApi = {
  /** Uploads a product photograph and opens an operation. */
  create(file: File): Promise<Operation> {
    return upload<Operation>('/operations', file)
  },

  /** Lists the caller's operations, newest first. */
  list(): Promise<OperationSummary[]> {
    return request<OperationSummary[]>('/operations')
  },

  /** Full detail of one operation. */
  get(id: string): Promise<Operation> {
    return request<Operation>(`/operations/${id}`)
  },

  /** Downloads the stored photograph as an object URL. */
  imageUrl(id: string): Promise<string> {
    return fetchBlobUrl(`/operations/${id}/image`)
  },

  /** Runs Claude vision over the photograph. */
  extract(id: string): Promise<Operation> {
    return request<Operation>(`/operations/${id}/extract`, { method: 'POST' })
  },

  /** Saves the user's corrections to the extracted name and function. */
  updateExtraction(id: string, name: string, functionText: string): Promise<Operation> {
    return request<Operation>(`/operations/${id}/extraction`, {
      method: 'PATCH',
      body: { name, function: functionText },
    })
  },

  /** Searches candidates and asks Claude to choose among them. */
  classify(id: string): Promise<Operation> {
    return request<Operation>(`/operations/${id}/classify`, { method: 'POST' })
  },

  /** Confirms the proposal, or replaces it with another catalog code. */
  confirmClassification(id: string, tariffCode: string, nico: string): Promise<Operation> {
    return request<Operation>(`/operations/${id}/classification`, {
      method: 'PATCH',
      body: { tariff_code: tariffCode, nico, confirmed_by_user: true },
    })
  },

  /** Saves the commercial data and settles the contributions. */
  saveDetails(id: string, details: OperationDetails): Promise<Operation> {
    return request<Operation>(`/operations/${id}/details`, {
      method: 'PATCH',
      body: details,
    })
  },

  /** Renders the simulated pedimento PDF. */
  generatePedimento(id: string): Promise<Operation> {
    return request<Operation>(`/operations/${id}/pedimento`, { method: 'POST' })
  },

  /** Downloads the pedimento as an object URL. */
  pedimentoUrl(id: string): Promise<string> {
    return fetchBlobUrl(`/operations/${id}/pedimento`)
  },
}

export const configApi = {
  /** Thresholds and form defaults owned by the server. */
  get(): Promise<AppConfig> {
    return request<AppConfig>('/config')
  },
}
