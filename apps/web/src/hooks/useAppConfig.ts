/**
 * Loads the server-owned configuration once per session.
 *
 * The review threshold and the form defaults live in the API's environment;
 * the UI reads them rather than restating them, so changing `.env` is enough
 * to change both sides.
 */

import { useEffect, useState } from 'react'

import { configApi } from '@/api/endpoints'
import type { AppConfig } from '@/types/api'

export function useAppConfig(): { config: AppConfig | null; isLoading: boolean } {
  const [config, setConfig] = useState<AppConfig | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    configApi
      .get()
      .then((loaded) => {
        if (!cancelled) setConfig(loaded)
      })
      .catch(() => {
        // The flow still works without it; only the preloaded defaults and the
        // meter's threshold tick depend on this call.
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  return { config, isLoading }
}
