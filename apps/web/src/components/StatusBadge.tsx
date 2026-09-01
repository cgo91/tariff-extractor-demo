/** Lifecycle status as a bordered tag, coloured by what it means for the user. */

import { STATUS_LABELS, type OperationStatus } from '@/types/api'

const TONE: Record<OperationStatus, string> = {
  created: 'border-rule-strong text-ink-soft',
  extracted: 'border-rule-strong text-ink-soft',
  classified: 'border-ink text-ink',
  pedimento_generated: 'border-verified text-verified',
  error: 'border-accent text-accent',
}

export function StatusBadge({ status }: { status: OperationStatus }) {
  return (
    <span
      className={`border px-2 py-0.5 text-xs font-semibold tracking-wide uppercase ${TONE[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  )
}
