/**
 * Step 1: upload a photograph and open an operation (RF-03).
 *
 * Once the operation exists it has an identifier, so the flow moves to its own
 * URL. That makes the browser's back button, a page reload and a link from the
 * history all behave the way a user expects.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ApiError } from '@/api/client'
import { operationsApi } from '@/api/endpoints'
import { ErrorNotice } from '@/components/ErrorNotice'
import { PhotoUpload } from '@/components/PhotoUpload'
import { StepTrail } from '@/components/StepTrail'

export function NewOperationPage() {
  const navigate = useNavigate()
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpload(file: File) {
    setIsUploading(true)
    setError(null)
    try {
      const created = await operationsApi.create(file)
      // `extract=1` tells the detail page to start the extraction on arrival.
      navigate(`/operaciones/${created.id}?extract=1`)
    } catch (caught) {
      setError(
        caught instanceof ApiError ? caught.message : 'No se pudo subir la imagen.',
      )
      setIsUploading(false)
    }
  }

  return (
    <div className="space-y-8">
      <header>
        <p className="eyebrow">Nueva operación</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          Clasifica una mercancía
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          Sube la fotografía del producto. Claude extrae sus características y
          propone una fracción arancelaria; tú decides cuál se usa.
        </p>
      </header>

      <StepTrail status={null} />

      {error ? <ErrorNotice message={error} /> : null}

      <PhotoUpload onSubmit={handleUpload} isSubmitting={isUploading} />
    </div>
  )
}
