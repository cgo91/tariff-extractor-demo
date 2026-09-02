/**
 * Progress through the operation.
 *
 * Numbered because the steps genuinely are a sequence with a fixed order —
 * you cannot classify before extracting — and the number tells the user how
 * much is left, not just where they are.
 *
 * The trail pins itself to the top of the viewport: the panels below it run
 * long enough that scrolling would otherwise leave the user without the one
 * cue that says where they are in the process. It is `sticky` rather than
 * `fixed` so it keeps the width of the column it belongs to and reserves its
 * own space in the flow instead of overlapping the content it scrolls past.
 *
 * The negative inline margin cancels the `px-6` of the layout's main element,
 * so the paper band spans the full column and nothing shows through at its
 * edges while the panels travel underneath.
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
    <div className="sticky top-0 z-30 -mx-6 bg-paper px-6 py-3">
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
    </div>
  )
}
