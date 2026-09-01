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

export interface Extraction {
  name: string
  brand: string | null
  model: string | null
  material: string | null
  function: string
  technical_specs: string[]
  visible_text: string | null
  search_keywords: string[]
}

export interface ClassificationAlternative {
  tariff_code: string
  formatted_code: string
  nico: string
  reason: string
}

export interface Classification {
  tariff_code: string
  formatted_code: string
  nico: string
  confidence: number
  rationale: string
  alternatives: ClassificationAlternative[]
  confirmed_by_user: boolean
  requires_review: boolean
  confidence_threshold: number
}

export interface Operation {
  id: string
  status: OperationStatus
  image_url: string
  extraction: Extraction | null
  candidates: TariffItem[]
  classification: Classification | null
  error_message: string | null
  has_pedimento: boolean
  created_at: string
  updated_at: string
}

export interface OperationSummary {
  id: string
  status: OperationStatus
  product_name: string | null
  tariff_code: string | null
  formatted_code: string | null
  confidence: number | null
  has_pedimento: boolean
  created_at: string
}

/** Human-readable Spanish label for each lifecycle status. */
export const STATUS_LABELS: Record<OperationStatus, string> = {
  created: 'Creada',
  extracted: 'Extraída',
  classified: 'Clasificada',
  pedimento_generated: 'Pedimento generado',
  error: 'Error',
}
