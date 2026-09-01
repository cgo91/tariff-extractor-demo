/**
 * Failure state with a way out.
 *
 * The non-functional requirements ask that an LLM failure be recoverable from
 * the UI, so this component always pairs the message with a retry action.
 */

interface ErrorNoticeProps {
  message: string
  onRetry?: () => void
  retryLabel?: string
  isRetrying?: boolean
}

export function ErrorNotice({
  message,
  onRetry,
  retryLabel = 'Reintentar',
  isRetrying = false,
}: ErrorNoticeProps) {
  return (
    <div role="alert" className="border-l-4 border-accent bg-accent-wash px-4 py-3">
      <p className="eyebrow text-accent">No se pudo completar el paso</p>
      <p className="mt-1 text-sm leading-relaxed text-ink">{message}</p>
      {onRetry ? (
        <button
          type="button"
          className="btn btn-secondary mt-3 py-1.5"
          onClick={onRetry}
          disabled={isRetrying}
        >
          {isRetrying ? 'Reintentando…' : retryLabel}
        </button>
      ) : null}
    </div>
  )
}
