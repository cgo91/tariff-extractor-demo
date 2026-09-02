/**
 * Commercial data of the operation (RF-07).
 *
 * Every field arrives preloaded from the server's configured defaults, so the
 * form is completed in one click during a demo. The values are still editable:
 * preloading is a convenience, not a decision made for the user.
 */

import { useEffect, useState, type FormEvent } from 'react'

import { FieldInput } from '@/components/Field'
import type { AppConfig, OperationDetails } from '@/types/api'

interface OperationDetailsFormProps {
  config: AppConfig
  /** Values already saved, when the user comes back to edit them. */
  saved: OperationDetails | null
  onSubmit: (details: OperationDetails) => Promise<void>
  isSubmitting: boolean
  /** Why the form is locked, shown under it; null means it accepts input. */
  disabledReason: string | null
}

interface FormState {
  invoiceValue: string
  quantity: string
  originCountry: string
  exchangeRate: string
  importerRfc: string
  importerName: string
  supplierName: string
  supplierCountry: string
}

function initialState(config: AppConfig, saved: OperationDetails | null): FormState {
  if (saved) {
    return {
      invoiceValue: String(saved.invoice_value_usd),
      quantity: String(saved.quantity),
      originCountry: saved.origin_country,
      exchangeRate: String(saved.exchange_rate),
      importerRfc: saved.importer.rfc,
      importerName: saved.importer.legal_name,
      supplierName: saved.supplier.name,
      supplierCountry: saved.supplier.country,
    }
  }
  return {
    invoiceValue: '100',
    quantity: '1',
    originCountry: config.defaults.origin_country,
    exchangeRate: String(config.defaults.exchange_rate),
    importerRfc: config.defaults.importer_rfc,
    importerName: config.defaults.importer_legal_name,
    supplierName: config.defaults.supplier_name,
    supplierCountry: config.defaults.supplier_country,
  }
}

/** Field-level messages; an empty object means the form can be submitted. */
function validate(state: FormState): Partial<Record<keyof FormState, string>> {
  const errors: Partial<Record<keyof FormState, string>> = {}

  const value = Number(state.invoiceValue)
  if (!Number.isFinite(value) || value <= 0) {
    errors.invoiceValue = 'Captura un valor mayor que cero.'
  }

  const quantity = Number(state.quantity)
  if (!Number.isInteger(quantity) || quantity <= 0) {
    errors.quantity = 'La cantidad debe ser un entero mayor que cero.'
  }

  const rate = Number(state.exchangeRate)
  if (!Number.isFinite(rate) || rate <= 0) {
    errors.exchangeRate = 'Captura un tipo de cambio mayor que cero.'
  }

  if (!/^[A-Za-z]{2}$/.test(state.originCountry)) {
    errors.originCountry = 'Usa el código ISO de 2 letras, por ejemplo CN.'
  }
  if (!/^[A-Za-z]{2}$/.test(state.supplierCountry)) {
    errors.supplierCountry = 'Usa el código ISO de 2 letras.'
  }
  if (state.importerRfc.trim().length < 12) {
    errors.importerRfc = 'El RFC debe tener 12 o 13 caracteres.'
  }
  if (state.importerName.trim().length < 2) {
    errors.importerName = 'Captura la razón social.'
  }
  if (state.supplierName.trim().length < 2) {
    errors.supplierName = 'Captura el nombre del proveedor.'
  }

  return errors
}

export function OperationDetailsForm({
  config,
  saved,
  onSubmit,
  isSubmitting,
  disabledReason,
}: OperationDetailsFormProps) {
  const disabled = disabledReason !== null
  const [state, setState] = useState<FormState>(() => initialState(config, saved))
  const [showErrors, setShowErrors] = useState(false)

  // Reload the saved values when the operation changes underneath the form.
  useEffect(() => {
    setState(initialState(config, saved))
    setShowErrors(false)
  }, [config, saved])

  const errors = validate(state)
  const isValid = Object.keys(errors).length === 0

  function update(field: keyof FormState, value: string) {
    setState((previous) => ({ ...previous, [field]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setShowErrors(true)
    if (!isValid) return

    await onSubmit({
      invoice_value_usd: Number(state.invoiceValue),
      quantity: Number(state.quantity),
      origin_country: state.originCountry.toUpperCase(),
      exchange_rate: Number(state.exchangeRate),
      importer: {
        rfc: state.importerRfc.trim().toUpperCase(),
        legal_name: state.importerName.trim(),
      },
      supplier: {
        name: state.supplierName.trim(),
        country: state.supplierCountry.toUpperCase(),
      },
    })
  }

  const errorFor = (field: keyof FormState) => (showErrors ? errors[field] : undefined)

  return (
    <section>
      <h2 className="text-lg font-semibold tracking-tight">Datos de la operación</h2>
      <p className="mt-1 text-sm text-ink-soft">
        {saved
          ? 'Los valores con los que se calcularon las contribuciones.'
          : 'Precargados con los valores de la demo. Ajusta lo que necesites.'}
      </p>

      <form onSubmit={handleSubmit} noValidate className="mt-4">
        <fieldset disabled={disabled} className="space-y-6">
          <div className="grid gap-2 sm:grid-cols-4">
            <FieldInput
              label="Valor factura (USD)"
              inputMode="decimal"
              value={state.invoiceValue}
              onChange={(event) => update('invoiceValue', event.target.value)}
              error={errorFor('invoiceValue')}
            />
            <FieldInput
              label="Cantidad"
              inputMode="numeric"
              value={state.quantity}
              onChange={(event) => update('quantity', event.target.value)}
              error={errorFor('quantity')}
            />
            <FieldInput
              label="País de origen"
              maxLength={2}
              value={state.originCountry}
              onChange={(event) => update('originCountry', event.target.value.toUpperCase())}
              error={errorFor('originCountry')}
            />
            <FieldInput
              label="Tipo de cambio"
              inputMode="decimal"
              value={state.exchangeRate}
              onChange={(event) => update('exchangeRate', event.target.value)}
              error={errorFor('exchangeRate')}
            />
          </div>

          <div>
            <h3 className="eyebrow">Importador</h3>
            <div className="mt-2 grid gap-2 sm:grid-cols-3">
              <FieldInput
                label="RFC"
                value={state.importerRfc}
                onChange={(event) => update('importerRfc', event.target.value.toUpperCase())}
                error={errorFor('importerRfc')}
              />
              <FieldInput
                label="Razón social"
                className="sm:col-span-2"
                value={state.importerName}
                onChange={(event) => update('importerName', event.target.value)}
                error={errorFor('importerName')}
              />
            </div>
          </div>

          <div>
            <h3 className="eyebrow">Proveedor</h3>
            <div className="mt-2 grid gap-2 sm:grid-cols-3">
              <FieldInput
                label="Nombre o razón social"
                className="sm:col-span-2"
                value={state.supplierName}
                onChange={(event) => update('supplierName', event.target.value)}
                error={errorFor('supplierName')}
              />
              <FieldInput
                label="País"
                maxLength={2}
                value={state.supplierCountry}
                onChange={(event) =>
                  update('supplierCountry', event.target.value.toUpperCase())
                }
                error={errorFor('supplierCountry')}
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
            {isSubmitting ? 'Calculando…' : 'Guardar y calcular contribuciones'}
          </button>
        </fieldset>
      </form>

      {disabledReason ? (
        <p className="mt-3 text-xs text-ink-faint">{disabledReason}</p>
      ) : null}
    </section>
  )
}
