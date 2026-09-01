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
  original_tariff_code: string | null
  was_overridden: boolean
  requires_review: boolean
  confidence_threshold: number
}

export interface Importer {
  rfc: string
  legal_name: string
}

export interface Supplier {
  name: string
  country: string
}

export interface OperationDetails {
  invoice_value_usd: number
  quantity: number
  origin_country: string
  exchange_rate: number
  importer: Importer
  supplier: Supplier
}

export interface Settlement {
  customs_value: number
  igi_amount: number
  dta_amount: number
  iva_amount: number
  total: number
}

export interface OperationDefaults {
  exchange_rate: number
  origin_country: string
  importer_rfc: string
  importer_legal_name: string
  supplier_name: string
  supplier_country: string
}

export interface AppConfig {
  confidence_threshold: number
  max_upload_bytes: number
  defaults: OperationDefaults
}

export interface Operation {
  id: string
  status: OperationStatus
  image_url: string
  extraction: Extraction | null
  candidates: TariffItem[]
  classification: Classification | null
  operation_details: OperationDetails | null
  settlement: Settlement | null
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
  nico: string | null
  confidence: number | null
  requires_review: boolean
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
