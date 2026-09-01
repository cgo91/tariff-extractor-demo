/**
 * Operation history (RF-10).
 *
 * A ruled table rather than a grid of cards: these rows are records, they are
 * read by scanning one column against another, and the tariff code has to line
 * up digit over digit for that scan to work.
 */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { ApiError } from '@/api/client'
import { operationsApi } from '@/api/endpoints'
import { ErrorNotice } from '@/components/ErrorNotice'
import { OperationThumbnail } from '@/components/OperationThumbnail'
import { StatusBadge } from '@/components/StatusBadge'
import type { OperationSummary } from '@/types/api'

const DATE_FORMAT = new Intl.DateTimeFormat('es-MX', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export function HistoryPage() {
  const [operations, setOperations] = useState<OperationSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    let cancelled = false
    setError(null)

    operationsApi
      .list()
      .then((rows) => {
        if (!cancelled) setOperations(rows)
      })
      .catch((caught) => {
        if (cancelled) return
        setError(
          caught instanceof ApiError ? caught.message : 'No se pudo cargar el historial.',
        )
      })

    return () => {
      cancelled = true
    }
  }, [reloadToken])

  return (
    <div className="space-y-8">
      <header>
        <p className="eyebrow">Registro</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Historial</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          Operaciones de la cuenta, de la más reciente a la más antigua.
        </p>
      </header>

      {error ? (
        <ErrorNotice message={error} onRetry={async () => setReloadToken((n) => n + 1)} />
      ) : null}

      {operations === null && !error ? <p className="eyebrow">Cargando…</p> : null}

      {operations !== null && operations.length === 0 ? (
        <div className="border border-dashed border-rule-strong bg-paper-sunk px-6 py-12 text-center">
          <p className="text-sm text-ink-soft">
            Todavía no hay operaciones registradas.
          </p>
          <Link to="/operaciones/nueva" className="btn btn-primary mt-4 inline-flex">
            Crear la primera
          </Link>
        </div>
      ) : null}

      {operations !== null && operations.length > 0 ? (
        <div className="overflow-x-auto border border-rule bg-white">
          <table className="w-full min-w-[52rem] border-collapse">
            <thead>
              <tr className="border-b border-ink">
                <th className="field-label px-3 py-2 text-left">Mercancía</th>
                <th className="field-label px-3 py-2 text-left">Fracción · NICO</th>
                <th className="field-label px-3 py-2 text-right">Confianza</th>
                <th className="field-label px-3 py-2 text-left">Estado</th>
                <th className="field-label px-3 py-2 text-left">Fecha</th>
                <th className="field-label px-3 py-2 text-right">Pedimento</th>
              </tr>
            </thead>
            <tbody>
              {operations.map((operation) => (
                <tr key={operation.id} className="border-b border-rule last:border-b-0">
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-3">
                      <OperationThumbnail
                        operationId={operation.id}
                        alt={operation.product_name ?? 'Mercancía sin identificar'}
                      />
                      <Link
                        to={`/operaciones/${operation.id}`}
                        className="text-sm font-medium underline decoration-rule-strong underline-offset-4 hover:decoration-accent"
                      >
                        {operation.product_name ?? 'Sin identificar'}
                      </Link>
                    </div>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-sm whitespace-nowrap tabular-nums">
                    {operation.formatted_code ? (
                      <>
                        {operation.formatted_code}
                        <span className="text-ink-faint"> · {operation.nico}</span>
                      </>
                    ) : (
                      <span className="text-ink-faint">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    {operation.confidence === null ? (
                      <span className="font-mono text-sm text-ink-faint">—</span>
                    ) : (
                      <span
                        className={`font-mono text-sm tabular-nums ${
                          operation.requires_review ? 'font-semibold text-flag' : ''
                        }`}
                        title={
                          operation.requires_review ? 'Requiere revisión manual' : undefined
                        }
                      >
                        {Math.round(operation.confidence * 100)}%
                        {operation.requires_review ? ' ⚑' : ''}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2.5">
                    <StatusBadge status={operation.status} />
                  </td>
                  <td className="px-3 py-2.5 text-sm whitespace-nowrap text-ink-soft">
                    {DATE_FORMAT.format(new Date(operation.created_at))}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    {operation.has_pedimento ? (
                      <Link
                        to={`/operaciones/${operation.id}`}
                        className="text-sm font-medium text-verified underline decoration-verified/40 underline-offset-4"
                      >
                        Ver PDF
                      </Link>
                    ) : (
                      <span className="text-sm text-ink-faint">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}
