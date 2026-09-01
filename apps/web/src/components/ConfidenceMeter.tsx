/**
 * Confidence read as an instrument, not as a progress bar.
 *
 * Ten discrete segments rather than a continuous gradient: a gauge with
 * countable ticks reads as a measurement, and it makes the difference between
 * 0.58 and 0.62 — the line that decides whether a human must intervene —
 * visible at a glance.
 */

const SEGMENTS = 10

interface ConfidenceMeterProps {
  /** Value between 0 and 1. */
  value: number
  /** Below this, the operation requires manual review. */
  threshold: number
}

export function ConfidenceMeter({ value, threshold }: ConfidenceMeterProps) {
  const percentage = Math.round(value * 100)
  const filled = Math.round(value * SEGMENTS)
  const isLow = value < threshold
  const thresholdSegment = Math.round(threshold * SEGMENTS)

  return (
    <div>
      <div className="flex items-baseline justify-between gap-4">
        <span className="field-label">Confianza</span>
        <span
          className={[
            'font-mono text-lg font-semibold tabular-nums',
            isLow ? 'text-flag' : 'text-verified',
          ].join(' ')}
        >
          {percentage}%
        </span>
      </div>

      <div
        className="mt-1.5 flex gap-px"
        role="meter"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Nivel de confianza de la clasificación"
      >
        {Array.from({ length: SEGMENTS }, (_, index) => {
          const isFilled = index < filled
          // The tick just past the threshold carries the review boundary.
          const isBoundary = index === thresholdSegment
          return (
            <span
              key={index}
              className={[
                'h-6 flex-1',
                isFilled ? (isLow ? 'bg-flag' : 'bg-verified') : 'bg-paper-sunk',
                isBoundary ? 'border-l-2 border-ink' : '',
              ].join(' ')}
            />
          )
        })}
      </div>

      <p className="mt-1.5 text-xs text-ink-faint">
        Umbral de revisión manual: {Math.round(threshold * 100)}%
      </p>
    </div>
  )
}
