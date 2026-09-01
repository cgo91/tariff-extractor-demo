/**
 * The pedimento field: the building block the whole interface is made of.
 *
 * A hairline box, a tiny uppercase label in the corner, and a monospaced
 * value — the same anatomy as a box on the Anexo 22 form the app produces.
 */

import type { InputHTMLAttributes, ReactNode } from 'react'
import { useId } from 'react'

interface FieldProps {
  label: string
  children: ReactNode
  /** Stretches the box across the available grid columns. */
  className?: string
}

/** Read-only field: a label and its value. */
export function Field({ label, children, className = '' }: FieldProps) {
  return (
    <div className={`field ${className}`}>
      <span className="field-label">{label}</span>
      <div className="field-value">{children}</div>
    </div>
  )
}

interface FieldInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'className'> {
  label: string
  /** Message shown under the box; also marks the input as invalid. */
  error?: string
  className?: string
}

/** Editable field: the same box, with an input inside it. */
export function FieldInput({ label, error, className = '', ...inputProps }: FieldInputProps) {
  const id = useId()
  const errorId = `${id}-error`

  return (
    <div className={className}>
      <div className="field">
        <label className="field-label" htmlFor={id}>
          {label}
        </label>
        <input
          id={id}
          className="field-input"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          {...inputProps}
        />
      </div>
      {error ? (
        <p id={errorId} className="mt-1.5 text-xs text-accent">
          {error}
        </p>
      ) : null}
    </div>
  )
}
