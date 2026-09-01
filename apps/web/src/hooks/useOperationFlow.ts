/**
 * State and actions for one operation, from extraction to pedimento.
 *
 * Extracted from the page because two routes drive the same flow: the one that
 * has just created an operation and the one that opens an existing operation
 * from the history.
 */

import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '@/api/client'
import { operationsApi } from '@/api/endpoints'
import type { Operation, OperationDetails } from '@/types/api'

/** Which long-running call is in flight, so only its control shows progress. */
export type PendingAction =
  | 'extract'
  | 'save'
  | 'classify'
  | 'confirm'
  | 'details'
  | 'pedimento'
  | null

export interface OperationFlow {
  operation: Operation | null
  imageUrl: string | null
  pending: PendingAction
  error: string | null
  isWorking: boolean
  setOperation: (operation: Operation) => void
  extract: () => Promise<void>
  saveExtraction: (name: string, functionText: string) => Promise<void>
  classify: () => Promise<void>
  confirmClassification: (tariffCode: string, nico: string) => Promise<void>
  saveDetails: (details: OperationDetails) => Promise<void>
  generatePedimento: () => Promise<void>
  retry: () => Promise<void>
}

function messageFor(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback
}

export function useOperationFlow(initial: Operation | null = null): OperationFlow {
  const [operation, setOperation] = useState<Operation | null>(initial)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [pending, setPending] = useState<PendingAction>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (initial) setOperation(initial)
  }, [initial])

  // The image endpoint requires the bearer token, so it cannot be an <img src>
  // straight to the API: it is fetched as a blob and revoked on replacement.
  const operationId = operation?.id ?? null
  useEffect(() => {
    if (operationId === null) {
      setImageUrl(null)
      return
    }

    let objectUrl: string | null = null
    let cancelled = false

    operationsApi
      .imageUrl(operationId)
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
  }, [operationId])

  /** Runs a step; on failure reloads so the persisted error status reaches the UI. */
  const run = useCallback(
    async (
      action: Exclude<PendingAction, null>,
      call: (id: string) => Promise<Operation>,
      fallbackMessage: string,
      reloadOnFailure = false,
    ) => {
      const id = operationId
      if (id === null) return

      setPending(action)
      setError(null)
      try {
        setOperation(await call(id))
      } catch (caught) {
        setError(messageFor(caught, fallbackMessage))
        if (reloadOnFailure) {
          try {
            setOperation(await operationsApi.get(id))
          } catch {
            // Keep the message already shown.
          }
        }
      } finally {
        setPending(null)
      }
    },
    [operationId],
  )

  const extract = useCallback(
    () =>
      run(
        'extract',
        (id) => operationsApi.extract(id),
        'No se pudo extraer las características.',
        true,
      ),
    [run],
  )

  const classify = useCallback(
    () =>
      run(
        'classify',
        (id) => operationsApi.classify(id),
        'No se pudo clasificar la mercancía.',
        true,
      ),
    [run],
  )

  const saveExtraction = useCallback(
    (name: string, functionText: string) =>
      run(
        'save',
        (id) => operationsApi.updateExtraction(id, name, functionText),
        'No se pudieron guardar los cambios.',
      ),
    [run],
  )

  const confirmClassification = useCallback(
    (tariffCode: string, nico: string) =>
      run(
        'confirm',
        (id) => operationsApi.confirmClassification(id, tariffCode, nico),
        'No se pudo confirmar la fracción.',
      ),
    [run],
  )

  const saveDetails = useCallback(
    (details: OperationDetails) =>
      run(
        'details',
        (id) => operationsApi.saveDetails(id, details),
        'No se pudieron guardar los datos de la operación.',
      ),
    [run],
  )

  const generatePedimento = useCallback(
    () =>
      run(
        'pedimento',
        (id) => operationsApi.generatePedimento(id),
        'No se pudo generar el pedimento.',
      ),
    [run],
  )

  /** Re-runs whichever step failed, which is what the error banner offers. */
  const retry = useCallback(
    () => (operation?.extraction ? classify() : extract()),
    [operation?.extraction, classify, extract],
  )

  return {
    operation,
    imageUrl,
    pending,
    error,
    isWorking: pending !== null,
    setOperation,
    extract,
    saveExtraction,
    classify,
    confirmClassification,
    saveDetails,
    generatePedimento,
    retry,
  }
}
