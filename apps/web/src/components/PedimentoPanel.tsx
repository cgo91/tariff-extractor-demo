/**
 * Pedimento generation and preview (RF-09).
 *
 * The PDF endpoint needs the bearer token, so the document is fetched as a
 * blob and shown from an object URL rather than pointed at directly.
 */

import { useEffect, useState } from 'react'

import { ApiError } from '@/api/client'
import { operationsApi } from '@/api/endpoints'

interface PedimentoPanelProps {
  operationId: string
  hasPedimento: boolean
  /** Missing prerequisite, when the document cannot be generated yet. */
  blockedReason: string | null
  onGenerate: () => Promise<void>
  isGenerating: boolean
}

export function PedimentoPanel({
  operationId,
  hasPedimento,
  blockedReason,
  onGenerate,
  isGenerating,
}: PedimentoPanelProps) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!hasPedimento) {
      setPdfUrl(null)
      return
    }

    let objectUrl: string | null = null
    let cancelled = false

    operationsApi
      .pedimentoUrl(operationId)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url)
          return
        }
        objectUrl = url
        setPdfUrl(url)
      })
      .catch((caught) => {
        if (cancelled) return
        setError(
          caught instanceof ApiError ? caught.message : 'No se pudo descargar el pedimento.',
        )
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [operationId, hasPedimento])

  return (
    <section>
      <h2 className="text-lg font-semibold tracking-tight">Pedimento</h2>
      <p className="mt-1 text-sm text-ink-soft">
        Documento simulado con layout inspirado en el Anexo 22. Sin validez legal.
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="btn btn-primary"
          onClick={onGenerate}
          disabled={isGenerating || blockedReason !== null}
        >
          {isGenerating
            ? 'Generando…'
            : hasPedimento
              ? 'Volver a generar'
              : 'Generar pedimento'}
        </button>

        {pdfUrl ? (
          <a
            href={pdfUrl}
            download={`pedimento-${operationId}.pdf`}
            className="btn btn-secondary"
          >
            Descargar PDF
          </a>
        ) : null}
      </div>

      {blockedReason ? (
        <p className="mt-3 text-xs text-ink-faint">{blockedReason}</p>
      ) : null}

      {error ? (
        <p
          role="alert"
          className="mt-3 border border-accent/35 bg-accent-wash px-3 py-2.5 text-sm text-accent-sunk"
        >
          {error}
        </p>
      ) : null}

      {pdfUrl ? (
        <iframe
          src={pdfUrl}
          title="Vista previa del pedimento"
          className="mt-4 h-[36rem] w-full border border-rule bg-white"
        />
      ) : null}
    </section>
  )
}
