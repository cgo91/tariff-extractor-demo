/**
 * One operation, at whatever step it stopped at (RF-04 to RF-10).
 *
 * Reached both after an upload and from the history table, which is why the
 * whole flow is driven by the operation loaded from the server rather than by
 * state carried across a navigation.
 */

import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'

import { ApiError } from '@/api/client'
import { operationsApi } from '@/api/endpoints'
import { ErrorNotice } from '@/components/ErrorNotice'
import { OperationWorkspace } from '@/components/OperationWorkspace'
import { StatusBadge } from '@/components/StatusBadge'
import { useAppConfig } from '@/hooks/useAppConfig'
import { useOperationFlow } from '@/hooks/useOperationFlow'
import type { Operation } from '@/types/api'

export function OperationDetailPage() {
  const { operationId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { config } = useAppConfig()

  const [loaded, setLoaded] = useState<Operation | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const flow = useOperationFlow(loaded)

  // Guards the auto-extraction so a re-render cannot fire a second call.
  const autoExtractStarted = useRef(false)

  useEffect(() => {
    let cancelled = false
    setLoadError(null)

    operationsApi
      .get(operationId)
      .then((operation) => {
        if (!cancelled) setLoaded(operation)
      })
      .catch((caught) => {
        if (cancelled) return
        setLoadError(
          caught instanceof ApiError ? caught.message : 'No se pudo cargar la operación.',
        )
      })

    return () => {
      cancelled = true
    }
  }, [operationId])

  // Arriving straight from the upload: start the extraction without a click.
  useEffect(() => {
    if (autoExtractStarted.current) return
    if (searchParams.get('extract') !== '1') return
    if (flow.operation?.status !== 'created') return

    autoExtractStarted.current = true
    setSearchParams({}, { replace: true })
    void flow.extract()
  }, [flow, searchParams, setSearchParams])

  if (loadError) {
    return (
      <div className="space-y-6">
        <ErrorNotice message={loadError} />
        <Link to="/operaciones" className="btn btn-secondary">
          Volver al historial
        </Link>
      </div>
    )
  }

  const operation = flow.operation
  if (operation === null) {
    return <p className="eyebrow">Cargando operación…</p>
  }

  return (
    <div className="space-y-8">
      <header>
        <div className="flex flex-wrap items-center gap-3">
          <p className="eyebrow">Operación</p>
          <span className="font-mono text-xs text-ink-faint">{operation.id}</span>
          <StatusBadge status={operation.status} />
        </div>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          {operation.extraction?.name ?? 'Mercancía sin identificar'}
        </h1>
      </header>

      <OperationWorkspace
        flow={flow}
        config={config}
        sidebarAction={
          <button
            type="button"
            className="btn btn-secondary w-full"
            onClick={() => navigate('/operaciones/nueva')}
          >
            Empezar otra operación
          </button>
        }
      />
    </div>
  )
}
