/**
 * Types mirroring the API contract.
 *
 * Field names match the backend exactly so that a response can be used without
 * a translation layer. User-facing labels are translated in the components.
 */

export type OperationStatus =
  | 'created'
  | 'extracted'
  | 'classified'
  | 'pedimento_generated'
  | 'error'

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface CurrentUser {
  id: string
  email: string
}

export interface TariffItem {
  tariff_code: string
  formatted_code: string
  nico: string
  description: string
  heading_description: string
  chapter: string
  unit_of_measure: string
  igi_rate: number
  iva_rate: number
}

export interface CatalogSearchResponse {
  query: string
  count: number
  results: TariffItem[]
}

export interface ApiErrorBody {
  code: string
  message: string
}
