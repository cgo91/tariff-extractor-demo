/**
 * The operation flow: upload, extract, review the features, classify.
 *
 * The whole flow lives on one page rather than across routes: the user is
 * meant to see the photograph, the features Claude read from it, and the
 * proposed tariff code at the same time, because judging the proposal means
 * comparing it against the evidence.
 */

import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/api/client'
import { operationsApi } from '@/api/endpoints'
import { ClassificationPanel } from '@/components/ClassificationPanel'
import { ErrorNotice } from '@/components/ErrorNotice'
import { ExtractionCard } from '@/components/ExtractionCard'
import { PhotoUpload } from '@/components/PhotoUpload'
import { StepTrail } from '@/components/StepTrail'
import type { Operation } from '@/types/api'

/** Which long-running call is in flight, so only its button shows a spinner. */
type PendingAction = 'upload' | 'extract' | 'save' | 'classify' | null

function messageFor(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

export function NewOperationPage() {
  const [operation, setOperation] = useState<Operation | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [pending, setPending] = useState<PendingAction>(null)
  const [error, setError] = useState<string | null>(null)

  // The image endpoint requires the bearer token, so it cannot be an <img src>
  // straight to the API: it is fetched as a blob and revoked on replacement.
  useEffect(() => {
    if (operation === null) {
      setImageUrl(null)
      return
    }

    let objectUrl: string | null = null
    let cancelled = false

    operationsApi
      .imageUrl(operation.id)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url)
          return
        }
        objectUrl = url
        setImageUrl(url)
      })
      .catch(() => {
        // A missing preview must not break the flow; the data still shows.
        if (!cancelled) setImageUrl(null)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [operation?.id])

  const runExtraction = useCallback(async (operationId: string) => {
    setPending('extract')
    setError(null)
    try {
      setOperation(await operationsApi.extract(operationId))
    } catch (caught) {
      setError(messageFor(caught, 'No se pudo extraer las características.'))
      // Reload so the persisted error status reaches the UI.
      try {
        setOperation(await operationsApi.get(operationId))
      } catch {
        // Keep the message already shown.
      }
    } finally {
      setPending(null)
    }
  }, [])

  async function handleUpload(file: File) {
    setPending('upload')
    setError(null)
    try {
      const created = await operationsApi.create(file)
      setOperation(created)
      await runExtraction(created.id)
    } catch (caught) {
      setError(messageFor(caught, 'No se pudo subir la imagen.'))
      setPending(null)
    }
  }

  async function handleSaveExtraction(name: string, functionText: string) {
    if (!operation) return
    setPending('save')
    setError(null)
    try {
      setOperation(await operationsApi.updateExtraction(operation.id, name, functionText))
    } catch (caught) {
      setError(messageFor(caught, 'No se pudieron guardar los cambios.'))
    } finally {
      setPending(null)
    }
  }

  async function handleClassify() {
    if (!operation) return
    setPending('classify')
    setError(null)
    try {
      setOperation(await operationsApi.classify(operation.id))
    } catch (caught) {
      setError(messageFor(caught, 'No se pudo clasificar la mercancía.'))
      try {
        setOperation(await operationsApi.get(operation.id))
      } catch {
        // Keep the message already shown.
      }
    } finally {
      setPending(null)
    }
  }

  function startOver() {
    setOperation(null)
    setError(null)
  }

  const isWorking = pending !== null

  return (
    <div className="space-y-8">
      <header>
        <p className="eyebrow">Nueva operación</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          {operation?.extraction?.name ?? 'Clasifica una mercancía'}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          Sube la fotografía del producto. Claude extrae sus características y
          propone una fracción arancelaria entre las del catálogo TIGIE.
        </p>
      </header>

      <StepTrail status={operation?.status ?? null} />

      {error ? (
        <ErrorNotice
          message={error}
          onRetry={
            operation
              ? operation.extraction
                ? handleClassify
                : () => runExtraction(operation.id)
              : undefined
          }
          isRetrying={isWorking}
        />
      ) : null}

      {operation === null ? (
        <PhotoUpload onSubmit={handleUpload} isSubmitting={pending === 'upload'} />
      ) : (
        <div className="grid gap-8 lg:grid-cols-[minmax(0,320px)_minmax(0,1fr)] lg:items-start">
          <aside className="space-y-3">
            {imageUrl ? (
              <img
                src={imageUrl}
                alt={operation.extraction?.name ?? 'Fotografía de la mercancía'}
                className="w-full border border-rule bg-white object-contain"
              />
            ) : (
              <div className="flex h-48 items-center justify-center border border-rule bg-paper-sunk">
                <span className="eyebrow">Sin vista previa</span>
              </div>
            )}
            <button type="button" className="btn btn-secondary w-full" onClick={startOver}>
              Empezar otra operación
            </button>
          </aside>

          <div className="space-y-8">
            {pending === 'extract' ? (
              <PendingPanel
                title="Extrayendo características"
                detail="Claude está leyendo la fotografía. Suele tardar menos de 20 segundos."
              />
            ) : null}

            {operation.extraction ? (
              <ExtractionCard
                extraction={operation.extraction}
                onSave={handleSaveExtraction}
                isSaving={pending === 'save'}
              />
            ) : null}

            {operation.extraction && !operation.classification ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleClassify}
                disabled={isWorking}
              >
                {pending === 'classify' ? 'Clasificando…' : 'Proponer fracción arancelaria'}
              </button>
            ) : null}

            {pending === 'classify' ? (
              <PendingPanel
                title="Buscando candidatos y clasificando"
                detail="Se consultan hasta 15 fracciones del catálogo y Claude elige entre ellas."
              />
            ) : null}

            {operation.classification ? (
              <>
                <ClassificationPanel
                  classification={operation.classification}
                  threshold={operation.classification.confidence_threshold}
                />
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handleClassify}
                    disabled={isWorking}
                  >
                    Volver a clasificar
                  </button>
                  <span className="text-xs text-ink-faint">
                    La revisión, los datos de la operación y el pedimento llegan en
                    la siguiente entrega.
                  </span>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}

/** Placeholder shown while a Claude call is in flight. */
function PendingPanel({ title, detail }: { title: string; detail: string }) {
  return (
    <div
      className="border border-rule bg-white px-4 py-4"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <span className="flex gap-1" aria-hidden="true">
          {[0, 1, 2].map((index) => (
            <span
              key={index}
              className="h-3 w-1.5 animate-pulse bg-accent"
              style={{ animationDelay: `${index * 160}ms` }}
            />
          ))}
        </span>
        <p className="text-sm font-semibold">{title}</p>
      </div>
      <p className="mt-1.5 text-sm text-ink-soft">{detail}</p>
    </div>
  )
}
