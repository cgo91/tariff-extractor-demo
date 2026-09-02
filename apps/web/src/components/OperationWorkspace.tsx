/**
 * Everything that happens to an operation once its photograph exists.
 *
 * The photograph stays pinned on the left while the panels scroll: judging a
 * proposed tariff code means comparing it against the evidence, so the evidence
 * has to remain on screen.
 */

import { ClassificationReview } from '@/components/ClassificationReview'
import { ErrorNotice } from '@/components/ErrorNotice'
import { ExtractionCard } from '@/components/ExtractionCard'
import { OperationDetailsForm } from '@/components/OperationDetailsForm'
import { PedimentoPanel } from '@/components/PedimentoPanel'
import { SettlementPanel } from '@/components/SettlementPanel'
import { StepTrail } from '@/components/StepTrail'
import type { OperationFlow } from '@/hooks/useOperationFlow'
import type { AppConfig, Operation } from '@/types/api'

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

/** IGI rate of the confirmed item, read from the candidates already loaded. */
function igiRateFor(operation: Operation): number | null {
  if (!operation.classification) return null
  const match = operation.candidates.find(
    (candidate) => candidate.tariff_code === operation.classification!.tariff_code,
  )
  return match?.igi_rate ?? null
}

interface OperationWorkspaceProps {
  flow: OperationFlow
  config: AppConfig | null
  /** Rendered under the photograph; differs between the two routes. */
  sidebarAction?: React.ReactNode
}

export function OperationWorkspace({ flow, config, sidebarAction }: OperationWorkspaceProps) {
  const { operation, imageUrl, pending, error, isWorking } = flow
  if (operation === null) return null

  // Once the pedimento exists the API rejects every edit with a 409, so the
  // panels show the record without offering controls that can only fail.
  const isLocked = operation.status === 'pedimento_generated'

  return (
    <div className="space-y-8">
      <StepTrail status={operation.status} />

      {error ? (
        <ErrorNotice message={error} onRetry={flow.retry} isRetrying={isWorking} />
      ) : null}

      <div className="grid gap-8 lg:grid-cols-[minmax(0,300px)_minmax(0,1fr)] lg:items-start">
        {/* Parks below the pinned step trail rather than under it. */}
        <aside className="space-y-3 lg:sticky lg:top-24">
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
          {sidebarAction}
        </aside>

        <div className="space-y-10">
          {pending === 'extract' ? (
            <PendingPanel
              title="Extrayendo características"
              detail="Claude está leyendo la fotografía. Suele tardar menos de 20 segundos."
            />
          ) : null}

          {!operation.extraction && pending !== 'extract' ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={flow.extract}
              disabled={isWorking}
            >
              Extraer características
            </button>
          ) : null}

          {operation.extraction ? (
            <ExtractionCard
              extraction={operation.extraction}
              status={operation.status}
              onSave={flow.saveExtraction}
              isSaving={pending === 'save'}
            />
          ) : null}

          {operation.extraction && !operation.classification ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={flow.classify}
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
                onConfirm={flow.confirmClassification}
                isConfirming={pending === 'confirm'}
                isLocked={isLocked}
              />

              {config ? (
                <OperationDetailsForm
                  config={config}
                  saved={operation.operation_details}
                  onSubmit={flow.saveDetails}
                  isSubmitting={pending === 'details'}
                  disabledReason={
                    isLocked
                      ? 'El pedimento ya fue generado: los datos de la operación quedaron fijados.'
                      : operation.classification.requires_review
                        ? 'Confirma la fracción arancelaria para capturar los datos de la operación.'
                        : null
                  }
                />
              ) : null}

              {operation.settlement ? (
                <SettlementPanel
                  settlement={operation.settlement}
                  igiRate={igiRateFor(operation)}
                />
              ) : null}

              <PedimentoPanel
                operationId={operation.id}
                hasPedimento={operation.has_pedimento}
                blockedReason={pedimentoBlockedReason(operation)}
                onGenerate={flow.generatePedimento}
                isGenerating={pending === 'pedimento'}
              />
            </>
          ) : null}
        </div>
      </div>
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
