/**
 * The proposal: tariff code, confidence, rationale and the runners-up.
 *
 * Read-only here. The review controls — confirming, switching to an
 * alternative, overriding from the catalog — arrive with RF-06.
 */

import { ConfidenceMeter } from '@/components/ConfidenceMeter'
import { Field } from '@/components/Field'
import type { Classification } from '@/types/api'

interface ClassificationPanelProps {
  classification: Classification
  threshold: number
}

export function ClassificationPanel({ classification, threshold }: ClassificationPanelProps) {
  return (
    <section>
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-lg font-semibold tracking-tight">Clasificación propuesta</h2>
        {classification.confirmed_by_user ? (
          <span className="eyebrow text-verified">Confirmada</span>
        ) : null}
      </div>

      {classification.requires_review ? (
        <div
          role="alert"
          className="mt-4 border-l-4 border-flag bg-flag-wash px-4 py-3"
        >
          <p className="eyebrow text-flag">Requiere revisión</p>
          <p className="mt-1 text-sm leading-relaxed text-ink">
            La confianza está por debajo del umbral. Revisa las alternativas y
            confirma manualmente una fracción antes de continuar.
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
        <ConfidenceMeter value={classification.confidence} threshold={threshold} />
      </div>

      <Field label="Justificación" className="mt-2 block">
        <p className="font-sans text-sm leading-relaxed text-ink-soft">
          {classification.rationale}
        </p>
      </Field>

      {classification.alternatives.length > 0 ? (
        <div className="mt-6">
          <h3 className="eyebrow">Alternativas consideradas</h3>
          <ul className="mt-2 divide-y divide-rule border border-rule bg-white">
            {classification.alternatives.map((alternative) => (
              <li
                key={`${alternative.tariff_code}-${alternative.nico}`}
                className="px-3 py-3"
              >
                <span className="font-mono text-sm font-semibold tabular-nums">
                  {alternative.formatted_code}
                  <span className="text-ink-faint"> · {alternative.nico}</span>
                </span>
                <p className="mt-1 text-sm leading-snug text-ink-soft">
                  {alternative.reason}
                </p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  )
}
