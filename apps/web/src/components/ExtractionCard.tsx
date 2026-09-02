/**
 * Extracted features, with the two fields the user may correct (RF-04).
 *
 * Name and function are editable because they are what drives the candidate
 * search: a wrong name sends the classifier down the wrong heading, and the
 * cheapest fix is a human typing three words.
 *
 * Once the pedimento exists the aggregate is closed and the API rejects the
 * edit with a 409, so the card turns read-only rather than offering a form
 * whose save can only fail.
 */

import { useEffect, useState } from 'react'

import { Field, FieldInput } from '@/components/Field'
import type { Extraction, OperationStatus } from '@/types/api'

interface ExtractionCardProps {
  extraction: Extraction
  status: OperationStatus
  onSave: (name: string, functionText: string) => Promise<void>
  isSaving: boolean
}

/** Mirrors `OperationService._reject_if_closed` on the API side. */
function editabilityFor(status: OperationStatus): { canEdit: boolean; note: string } {
  if (status === 'pedimento_generated') {
    return { canEdit: false, note: 'Solo lectura · pedimento generado' }
  }
  if (status === 'classified') {
    return { canEdit: true, note: 'Nombre y función editables · vuelve a clasificar' }
  }
  return { canEdit: true, note: 'Nombre y función editables antes de clasificar' }
}

export function ExtractionCard({
  extraction,
  status,
  onSave,
  isSaving,
}: ExtractionCardProps) {
  const [name, setName] = useState(extraction.name)
  const [functionText, setFunctionText] = useState(extraction.function)

  // A re-extraction replaces the whole card; the inputs follow it.
  useEffect(() => {
    setName(extraction.name)
    setFunctionText(extraction.function)
  }, [extraction])

  const { canEdit, note } = editabilityFor(status)
  const isDirty = name !== extraction.name || functionText !== extraction.function
  const isValid = name.trim().length >= 2 && functionText.trim().length >= 2

  return (
    <section>
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-lg font-semibold tracking-tight">Características extraídas</h2>
        <span className="eyebrow">{note}</span>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {canEdit ? (
          <>
            <FieldInput
              label="Nombre del producto"
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="sm:col-span-2"
            />
            <FieldInput
              label="Función"
              value={functionText}
              onChange={(event) => setFunctionText(event.target.value)}
              className="sm:col-span-2"
            />
          </>
        ) : (
          <>
            <Field label="Nombre del producto" className="sm:col-span-2">
              {extraction.name}
            </Field>
            <Field label="Función" className="sm:col-span-2">
              {extraction.function}
            </Field>
          </>
        )}

        <Field label="Marca">{extraction.brand ?? '—'}</Field>
        <Field label="Modelo">{extraction.model ?? '—'}</Field>
        <Field label="Material">{extraction.material ?? '—'}</Field>
        <Field label="Texto visible">{extraction.visible_text ?? '—'}</Field>

        <Field label="Características técnicas" className="sm:col-span-2">
          {extraction.technical_specs.length > 0 ? (
            <ul className="space-y-0.5">
              {extraction.technical_specs.map((spec) => (
                <li key={spec}>· {spec}</li>
              ))}
            </ul>
          ) : (
            '—'
          )}
        </Field>

        <Field label="Palabras clave de búsqueda" className="sm:col-span-2">
          {extraction.search_keywords.join(' · ') || '—'}
        </Field>
      </div>

      {canEdit && isDirty ? (
        <div className="mt-3 flex items-center gap-3">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={!isValid || isSaving}
            onClick={() => onSave(name.trim(), functionText.trim())}
          >
            {isSaving ? 'Guardando…' : 'Guardar cambios'}
          </button>
          <span className="text-xs text-ink-faint">
            Guarda antes de clasificar para que la búsqueda use el texto corregido.
          </span>
        </div>
      ) : null}
    </section>
  )
}
