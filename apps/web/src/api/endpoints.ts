/** Typed wrappers around the API routes, grouped by resource. */

import { request } from '@/api/client'
import type { CatalogSearchResponse, CurrentUser, LoginResponse } from '@/types/api'

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
