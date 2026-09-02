/**
 * Manual tariff catalog search.
 *
 * Built now because the review screen (RF-06) needs exactly this control to let
 * the user override the proposal with any code in the catalog. `onSelect` is
 * what the review screen will pass; without it the component is a plain lookup.
 */

import { useEffect, useRef, useState } from 'react'

import { ApiError } from '@/api/client'
import { catalogApi } from '@/api/endpoints'
import type { TariffItem } from '@/types/api'

const MIN_QUERY_LENGTH = 2
const DEBOUNCE_MS = 300

interface CatalogSearchProps {
  /** Called when the user picks a result. Omit for a read-only lookup. */
  onSelect?: (item: TariffItem) => void
  /** Code currently chosen elsewhere, highlighted in the list. */
  selectedCode?: string
}

export function CatalogSearch({ onSelect, selectedCode }: CatalogSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<TariffItem[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const trimmed = query.trim()
    if (trimmed.length < MIN_QUERY_LENGTH) {
      setResults([])
      setHasSearched(false)
      setError(null)
      return
    }

    const timer = window.setTimeout(async () => {
      controllerRef.current?.abort()
      const controller = new AbortController()
      controllerRef.current = controller

      setIsSearching(true)
      setError(null)
      try {
        const response = await catalogApi.search(trimmed, controller.signal)
        setResults(response.results)
        setHasSearched(true)
      } catch (caught) {
        if (controller.signal.aborted) return
        setError(
          caught instanceof ApiError
            ? caught.message
            : 'No se pudo consultar el catálogo.',
        )
        setResults([])
      } finally {
        if (!controller.signal.aborted) setIsSearching(false)
      }
    }, DEBOUNCE_MS)

    return () => window.clearTimeout(timer)
  }, [query])

  return (
    <section>
      <div className="field field-editable">
        <label className="field-label" htmlFor="catalog-query">
          Buscar en el catálogo TIGIE
        </label>
        <input
          id="catalog-query"
          type="search"
          className="field-input"
          placeholder="audífonos bluetooth"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          autoComplete="off"
        />
      </div>

      <div className="mt-2 flex items-center justify-between text-xs text-ink-faint">
        <span>Escribe al menos {MIN_QUERY_LENGTH} caracteres. Máximo 15 resultados.</span>
        {isSearching ? <span className="eyebrow">Buscando…</span> : null}
      </div>

      {error ? (
        <p
          role="alert"
          className="mt-3 border border-accent/35 bg-accent-wash px-3 py-2.5 text-sm text-accent-sunk"
        >
          {error}
        </p>
      ) : null}

      {hasSearched && results.length === 0 && !isSearching && !error ? (
        <p className="mt-3 border border-rule bg-paper-sunk px-3 py-3 text-sm text-ink-soft">
          Sin coincidencias. Prueba con el nombre genérico del producto, por
          ejemplo «altavoces» en lugar de la marca.
        </p>
      ) : null}

      {results.length > 0 ? (
        <ul className="mt-3 divide-y divide-rule border border-rule bg-white">
          {results.map((item) => {
            const isSelected = item.tariff_code === selectedCode
            const content = (
              <>
                <div className="flex items-baseline justify-between gap-4">
                  <span className="font-mono text-sm font-semibold tabular-nums">
                    {item.formatted_code}
                    <span className="text-ink-faint"> · {item.nico}</span>
                  </span>
                  <span className="font-mono text-xs whitespace-nowrap text-ink-faint tabular-nums">
                    IGI {(item.igi_rate * 100).toFixed(0)}% · {item.unit_of_measure}
                  </span>
                </div>
                <p className="mt-1 text-sm leading-snug text-ink-soft">
                  {item.description}
                </p>
              </>
            )

            return (
              <li key={`${item.tariff_code}-${item.nico}`}>
                {onSelect ? (
                  <button
                    type="button"
                    onClick={() => onSelect(item)}
                    className={[
                      'block w-full px-3 py-3 text-left transition-colors hover:bg-paper-sunk',
                      isSelected ? 'bg-verified-wash' : '',
                    ].join(' ')}
                  >
                    {content}
                  </button>
                ) : (
                  <div className="px-3 py-3">{content}</div>
                )}
              </li>
            )
          })}
        </ul>
      ) : null}
    </section>
  )
}
