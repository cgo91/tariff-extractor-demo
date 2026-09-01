/**
 * New operation (RF-03 / RF-04).
 *
 * Phase 1 ships the shell plus the working catalog lookup; the photo upload and
 * the Claude extraction land in phase 2.
 */

import { CatalogSearch } from '@/components/CatalogSearch'

export function NewOperationPage() {
  return (
    <div className="space-y-10">
      <header>
        <p className="eyebrow">Paso 1 de 4</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Nueva operación</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          Sube la fotografía del producto para extraer sus características y
          proponer una fracción arancelaria.
        </p>
      </header>

      <section className="border border-dashed border-rule-strong bg-paper-sunk px-6 py-10 text-center">
        <p className="eyebrow">Carga de fotografía</p>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-ink-soft">
          Disponible en la siguiente entrega: selector de archivo con vista
          previa, validación de JPG y PNG hasta 10 MB, y extracción con Claude
          vision.
        </p>
      </section>

      <section>
        <h2 className="text-lg font-semibold tracking-tight">Consulta del catálogo</h2>
        <p className="mt-1 mb-4 max-w-2xl text-sm text-ink-soft">
          El mismo buscador que permitirá corregir manualmente la fracción
          propuesta.
        </p>
        <CatalogSearch />
      </section>
    </div>
  )
}
