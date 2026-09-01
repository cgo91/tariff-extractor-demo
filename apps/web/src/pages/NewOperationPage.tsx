/**
 * The whole operation flow on one page: upload, extract, review, capture,
 * generate.
 *
 * One page rather than four routes, because judging the proposal means
 * comparing it against the evidence: the photograph, the features Claude read
 * from it, and the code it chose all have to be visible at once.
 */

import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/api/client'
import { operationsApi } from '@/api/endpoints'
import { ClassificationReview } from '@/components/ClassificationReview'
import { ErrorNotice } from '@/components/ErrorNotice'
import { ExtractionCard } from '@/components/ExtractionCard'
import { OperationDetailsForm } from '@/components/OperationDetailsForm'
import { PedimentoPanel } from '@/components/PedimentoPanel'
import { PhotoUpload } from '@/components/PhotoUpload'
import { SettlementPanel } from '@/components/SettlementPanel'
import { StepTrail } from '@/components/StepTrail'
import { useAppConfig } from '@/hooks/useAppConfig'
import type { Operation, OperationDetails } from '@/types/api'

/** Which long-running call is in flight, so only its control shows progress. */
type PendingAction =
  | 'upload'
  | 'extract'
  | 'save'
  | 'classify'
  | 'confirm'
  | 'details'
  | 'pedimento'
  | null

function messageFor(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

/** The missing prerequisite for generating the pedimento, if any. */
function pedimentoBlockedReason(operation: Operation): string | null {
  if (!operation.classification) {
    return 'Clasifica la mercancía antes de generar el pedimento.'
  }
  if (operation.classification.requires_review) {
    return 'La confianza está por debajo del umbral: confirma una fracción para continuar.'
  }
  if (!operation.settlement) {
    return 'Captura los datos de la operación para calcular las contribuciones.'
  }
  return null
}

export function NewOperationPage() {
  const { config } = useAppConfig()
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

  /** Runs a step, and on failure reloads so the persisted error status shows. */
  const runStep = useCallback(
    async (
      action: Exclude<PendingAction, null>,
      call: () => Promise<Operation>,
      fallbackMessage: string,
      operationId?: string,
    ) => {
      setPending(action)
      setError(null)
      try {
        setOperation(await call())
      } catch (caught) {
        setError(messageFor(caught, fallbackMessage))
        if (operationId) {
          try {
            setOperation(await operationsApi.get(operationId))
          } catch {
            // Keep the message already shown.
          }
        }
      } finally {
        setPending(null)
      }
    },
    [],
  )

  const runExtraction = useCallback(
    (operationId: string) =>
      runStep(
        'extract',
        () => operationsApi.extract(operationId),
        'No se pudo extraer las características.',
        operationId,
      ),
    [runStep],
  )

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

  const handleSaveExtraction = (name: string, functionText: string) =>
    runStep(
      'save',
      () => operationsApi.updateExtraction(operation!.id, name, functionText),
      'No se pudieron guardar los cambios.',
    )

  const handleClassify = () =>
    runStep(
      'classify',
      () => operationsApi.classify(operation!.id),
      'No se pudo clasificar la mercancía.',
      operation?.id,
    )

  const handleConfirm = (tariffCode: string, nico: string) =>
    runStep(
      'confirm',
      () => operationsApi.confirmClassification(operation!.id, tariffCode, nico),
      'No se pudo confirmar la fracción.',
    )

  const handleSaveDetails = (details: OperationDetails) =>
    runStep(
      'details',
      () => operationsApi.saveDetails(operation!.id, details),
      'No se pudieron guardar los datos de la operación.',
    )

  const handleGeneratePedimento = () =>
    runStep(
      'pedimento',
      () => operationsApi.generatePedimento(operation!.id),
      'No se pudo generar el pedimento.',
    )

  function startOver() {
    setOperation(null)
    setError(null)
  }

  const isWorking = pending !== null
  const igiRate =
    operation?.classification
      ? (operation.candidates.find(
          (candidate) => candidate.tariff_code === operation.classification!.tariff_code,
        )?.igi_rate ?? null)
      : null

  return (
    <div className="space-y-8">
      <header>
        <p className="eyebrow">Nueva operación</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          {operation?.extraction?.name ?? 'Clasifica una mercancía'}
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          Sube la fotografía del producto. Claude extrae sus características y
          propone una fracción arancelaria; tú decides cuál se usa.
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
        <div className="grid gap-8 lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)] lg:items-start">
          <aside className="space-y-3 lg:sticky lg:top-6">
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

          <div className="space-y-10">
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
                <ClassificationReview
                  classification={operation.classification}
                  candidates={operation.candidates}
                  onConfirm={handleConfirm}
                  isConfirming={pending === 'confirm'}
                />

                {config ? (
                  <OperationDetailsForm
                    config={config}
                    saved={operation.operation_details}
                    onSubmit={handleSaveDetails}
                    isSubmitting={pending === 'details'}
                    disabled={operation.classification.requires_review}
                  />
                ) : null}

                {operation.settlement ? (
                  <SettlementPanel settlement={operation.settlement} igiRate={igiRate} />
                ) : null}

                <PedimentoPanel
                  operationId={operation.id}
                  hasPedimento={operation.has_pedimento}
                  blockedReason={pedimentoBlockedReason(operation)}
                  onGenerate={handleGeneratePedimento}
                  isGenerating={pending === 'pedimento'}
                />
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
    <div className="border border-rule bg-white px-4 py-4" role="status" aria-live="polite">
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
