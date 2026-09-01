/**
 * Photo picker with preview (RF-03).
 *
 * Validates size and type in the browser so an obvious mistake is caught
 * before a round trip; the server validates again, because a client check is a
 * courtesy and never a guarantee.
 */

import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react'

const MAX_BYTES = 10 * 1024 * 1024
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'image/heif']

interface PhotoUploadProps {
  onSubmit: (file: File) => void
  isSubmitting: boolean
}

export function PhotoUpload({ onSubmit, isSubmitting }: PhotoUploadProps) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDraggingOver, setIsDraggingOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  // Object URLs are revoked on replacement and on unmount, otherwise every
  // preview leaks a blob for the lifetime of the tab.
  useEffect(() => {
    if (file === null) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function accept(candidate: File | undefined) {
    if (!candidate) return

    if (!ACCEPTED_TYPES.includes(candidate.type)) {
      setError('Formato no admitido. Sube una imagen JPG o PNG.')
      setFile(null)
      return
    }
    if (candidate.size > MAX_BYTES) {
      setError(
        `La imagen pesa ${(candidate.size / 1024 / 1024).toFixed(1)} MB y el máximo es 10 MB.`,
      )
      setFile(null)
      return
    }

    setError(null)
    setFile(candidate)
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    accept(event.target.files?.[0])
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDraggingOver(false)
    accept(event.dataTransfer.files?.[0])
  }

  function reset() {
    setFile(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <section>
      <div
        onDragOver={(event) => {
          event.preventDefault()
          setIsDraggingOver(true)
        }}
        onDragLeave={() => setIsDraggingOver(false)}
        onDrop={handleDrop}
        className={[
          'border border-dashed px-6 py-8 text-center transition-colors',
          isDraggingOver ? 'border-accent bg-accent-wash' : 'border-rule-strong bg-paper-sunk',
        ].join(' ')}
      >
        {previewUrl && file ? (
          <div className="flex flex-col items-center gap-4">
            <img
              src={previewUrl}
              alt={`Vista previa de ${file.name}`}
              className="max-h-64 border border-rule bg-white object-contain"
            />
            <div className="grid w-full max-w-md grid-cols-2 gap-px bg-rule">
              <div className="field border-0">
                <span className="field-label">Archivo</span>
                <span className="field-value block truncate">{file.name}</span>
              </div>
              <div className="field border-0">
                <span className="field-label">Tamaño</span>
                <span className="field-value block">
                  {(file.size / 1024).toFixed(0)} KB
                </span>
              </div>
            </div>
          </div>
        ) : (
          <>
            <p className="eyebrow">Fotografía del producto</p>
            <p className="mx-auto mt-3 max-w-sm text-sm leading-relaxed text-ink-soft">
              Arrastra la imagen aquí o selecciónala. JPG o PNG, hasta 10 MB.
              Fondo liso y buena luz mejoran la extracción.
            </p>
          </>
        )}

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(',')}
          onChange={handleChange}
          className="sr-only"
          id="photo-input"
        />

        <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
          <label htmlFor="photo-input" className="btn btn-secondary cursor-pointer">
            {file ? 'Cambiar imagen' : 'Seleccionar imagen'}
          </label>
          {file ? (
            <button type="button" className="btn btn-secondary" onClick={reset}>
              Quitar
            </button>
          ) : null}
        </div>
      </div>

      {error ? (
        <p
          role="alert"
          className="mt-3 border border-accent/35 bg-accent-wash px-3 py-2.5 text-sm text-accent-sunk"
        >
          {error}
        </p>
      ) : null}

      <button
        type="button"
        className="btn btn-primary mt-4 w-full sm:w-auto"
        disabled={file === null || isSubmitting}
        onClick={() => file && onSubmit(file)}
      >
        {isSubmitting ? 'Subiendo…' : 'Subir y extraer características'}
      </button>
    </section>
  )
}
