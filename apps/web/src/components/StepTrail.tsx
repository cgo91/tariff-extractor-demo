/**
 * Progress through the operation.
 *
 * Numbered because the steps genuinely are a sequence with a fixed order —
 * you cannot classify before extracting — and the number tells the user how
 * much is left, not just where they are.
 */

import type { OperationStatus } from '@/types/api'

const STEPS = [
  { key: 'upload', label: 'Fotografía' },
  { key: 'extract', label: 'Extracción' },
  { key: 'classify', label: 'Fracción · NICO' },
  { key: 'pedimento', label: 'Pedimento' },
] as const

/** Index of the step the given status has already completed. */
function completedThrough(status: OperationStatus | null): number {
  switch (status) {
    case 'created':
      return 0
    case 'extracted':
      return 1
    case 'classified':
      return 2
    case 'pedimento_generated':
      return 3
    default:
      return -1
  }
}

interface StepTrailProps {
  status: OperationStatus | null
}

export function StepTrail({ status }: StepTrailProps) {
  const completed = completedThrough(status)

  return (
    <ol className="grid grid-cols-2 gap-px border border-rule bg-rule sm:grid-cols-4">
      {STEPS.map((step, index) => {
        const isDone = index <= completed
        const isCurrent = index === completed + 1
        return (
          <li
            key={step.key}
            className={[
              'px-3 py-2.5',
              isDone ? 'bg-ink text-paper' : 'bg-white',
              isCurrent ? 'border-l-2 border-accent' : '',
            ].join(' ')}
            aria-current={isCurrent ? 'step' : undefined}
          >
            <span
              className={[
                'field-label',
                isDone ? 'text-paper/50' : isCurrent ? 'text-accent' : 'text-ink-faint',
              ].join(' ')}
            >
              Paso {index + 1}
            </span>
            <span
              className={[
                'mt-0.5 block text-sm font-medium',
                isDone ? 'text-paper' : isCurrent ? 'text-ink' : 'text-ink-faint',
              ].join(' ')}
            >
              {step.label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}
