/**
 * Row thumbnail for the history table.
 *
 * Each row fetches its own image because the endpoint needs the bearer token,
 * and it only starts once the row is on screen: a long history should not open
 * fifty requests on load.
 */

import { useEffect, useRef, useState } from 'react'

import { operationsApi } from '@/api/endpoints'

export function OperationThumbnail({ operationId, alt }: { operationId: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [isVisible, setIsVisible] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const node = containerRef.current
    if (node === null) return

    // Browsers without IntersectionObserver just load everything.
    if (typeof IntersectionObserver === 'undefined') {
      setIsVisible(true)
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setIsVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin: '200px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!isVisible) return

    let objectUrl: string | null = null
    let cancelled = false

    operationsApi
      .imageUrl(operationId)
      .then((loaded) => {
        if (cancelled) {
          URL.revokeObjectURL(loaded)
          return
        }
        objectUrl = loaded
        setUrl(loaded)
      })
      .catch(() => {
        // An unavailable image leaves the placeholder in place.
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [isVisible, operationId])

  return (
    <div
      ref={containerRef}
      className="h-12 w-16 shrink-0 overflow-hidden border border-rule bg-paper-sunk"
    >
      {url ? (
        <img src={url} alt={alt} className="h-full w-full object-cover" loading="lazy" />
      ) : null}
    </div>
  )
}
