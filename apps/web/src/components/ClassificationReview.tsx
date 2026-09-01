/**
 * The review step (RF-06): the moment the product exists for.
 *
 * The proposal is shown with its evidence — confidence, rationale, the codes
 * that were considered and discarded — and three ways to act on it: accept it,
 * take one of the alternatives, or search the catalog for anything else.
 * Below the confidence threshold nothing moves forward until a person picks.
 */

import { useState } from 'react'

import { CatalogSearch } from '@/components/CatalogSearch'
import { ConfidenceMeter } from '@/components/ConfidenceMeter'
import { Field } from '@/components/Field'
import type { Classification, TariffItem } from '@/types/api'

interface ClassificationReviewProps {
  classification: Classification
  candidates: TariffItem[]
  onConfirm: (tariffCode: string, nico: string) => Promise<void>
  isConfirming: boolean
}

function formatCode(tariffCode: string): string {
  return `${tariffCode.slice(0, 4)}.${tariffCode.slice(4, 6)}.${tariffCode.slice(6, 8)}`
}

export function ClassificationReview({
  classification,
  candidates,
  onConfirm,
  isConfirming,
}: ClassificationReviewProps) {
  const [isSearching, setIsSearching] = useState(false)

  return (
    <section>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-lg font-semibold tracking-tight">Clasificación propuesta</h2>
        {classification.confirmed_by_user ? (
          <span className="border border-verified px-2 py-0.5 text-xs font-semibold tracking-wide text-verified uppercase">
            {classification.was_overridden
              ? 'Corregida por el usuario'
              : 'Confirmada por el usuario'}
          </span>
        ) : null}
      </div>

      {classification.requires_review ? (
        <div role="alert" className="mt-4 border-l-4 border-flag bg-flag-wash px-4 py-3">
          <p className="eyebrow text-flag">Requiere revisión</p>
          <p className="mt-1 text-sm leading-relaxed text-ink">
            La confianza está por debajo del umbral. Confirma una fracción —esta
            o cualquier otra del catálogo— antes de continuar.
          </p>
        </div>
      ) : null}

      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        <div className="field sm:col-span-2">
          <span className="field-label">Fracción arancelaria</span>
          <span className="block font-mono text-3xl font-semibold tracking-tight tabular-nums">
            {classification.formatted_code}
          </span>
        </div>
        <Field label="NICO">
          <span className="text-3xl font-semibold">{classification.nico}</span>
        </Field>
      </div>

      <div className="mt-2 border border-rule bg-white px-3 py-3">
        <ConfidenceMeter
          value={classification.confidence}
          threshold={classification.confidence_threshold}
        />
      </div>

      <div className="field mt-2">
        <span className="field-label">Justificación</span>
        <p className="mt-0.5 text-sm leading-relaxed text-ink-soft">
          {classification.rationale}
        </p>
      </div>

      {classification.was_overridden && classification.original_tariff_code ? (
        <p className="mt-2 border-l-2 border-rule-strong px-3 py-1.5 text-xs text-ink-soft">
          El modelo había propuesto{' '}
          <span className="font-mono">
            {formatCode(classification.original_tariff_code)}
          </span>
          ; la fracción vigente fue elegida en la revisión manual.
        </p>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => onConfirm(classification.tariff_code, classification.nico)}
          disabled={isConfirming}
        >
          {isConfirming ? 'Guardando…' : 'Confirmar esta fracción'}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => setIsSearching((open) => !open)}
        >
          {isSearching ? 'Cerrar buscador' : 'Elegir otra del catálogo'}
        </button>
      </div>

      {isSearching ? (
        <div className="mt-4 border border-rule bg-paper-sunk p-4">
          <CatalogSearch
            selectedCode={classification.tariff_code}
            onSelect={(item) => {
              void onConfirm(item.tariff_code, item.nico)
              setIsSearching(false)
            }}
          />
        </div>
      ) : null}

      {classification.alternatives.length > 0 ? (
        <div className="mt-8">
          <h3 className="eyebrow">Alternativas consideradas</h3>
          <p className="mt-1 mb-2 text-xs text-ink-faint">
            Selecciona una para sustituir la propuesta.
          </p>
          <ul className="divide-y divide-rule border border-rule bg-white">
            {classification.alternatives.map((alternative) => (
              <li key={`${alternative.tariff_code}-${alternative.nico}`}>
                <button
                  type="button"
                  className="block w-full px-3 py-3 text-left transition-colors hover:bg-paper-sunk disabled:opacity-50"
                  onClick={() => onConfirm(alternative.tariff_code, alternative.nico)}
                  disabled={isConfirming}
                >
                  <span className="font-mono text-sm font-semibold tabular-nums">
                    {alternative.formatted_code}
                    <span className="text-ink-faint"> · {alternative.nico}</span>
                  </span>
                  <p className="mt-1 text-sm leading-snug text-ink-soft">
                    {alternative.reason}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {candidates.length > 0 ? (
        <details className="mt-6 border border-rule bg-white">
          <summary className="cursor-pointer px-3 py-2.5 text-sm font-medium">
            Ver los {candidates.length} candidatos que se enviaron al modelo
          </summary>
          <ul className="divide-y divide-rule border-t border-rule">
            {candidates.map((candidate) => (
              <li
                key={`${candidate.tariff_code}-${candidate.nico}`}
                className="flex items-baseline gap-3 px-3 py-2"
              >
                <span className="font-mono text-xs whitespace-nowrap tabular-nums">
                  {candidate.formatted_code}
                </span>
                <span className="truncate text-xs text-ink-soft">
                  {candidate.description}
                </span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  )
}
