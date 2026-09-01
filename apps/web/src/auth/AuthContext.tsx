/**
 * Session state.
 *
 * The token lives in localStorage so a page reload keeps the session, and is
 * validated against /auth/me on boot: a token that expired while the tab was
 * closed must not leave the UI in a half-authenticated state.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

import { setTokenReader } from '@/api/client'
import { authApi } from '@/api/endpoints'
import type { CurrentUser } from '@/types/api'

const TOKEN_STORAGE_KEY = 'tariff-assistant.access-token'

interface AuthContextValue {
  user: CurrentUser | null
  isAuthenticated: boolean
  /** True while the stored token is being validated on boot. */
  isRestoring: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readStoredToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    // Private browsing modes can throw on storage access.
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const tokenRef = useRef<string | null>(readStoredToken())
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [isRestoring, setIsRestoring] = useState(tokenRef.current !== null)

  // The HTTP client reads the token through a ref so it always sees the
  // current value without the provider having to re-register on every change.
  useEffect(() => {
    setTokenReader(() => tokenRef.current)
  }, [])

  const persistToken = useCallback((token: string | null) => {
    tokenRef.current = token
    try {
      if (token) {
        window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
      } else {
        window.localStorage.removeItem(TOKEN_STORAGE_KEY)
      }
    } catch {
      // Falling back to in-memory only is acceptable for the demo.
    }
  }, [])

  const signOut = useCallback(() => {
    persistToken(null)
    setUser(null)
  }, [persistToken])

  const signIn = useCallback(
    async (email: string, password: string) => {
      const session = await authApi.login(email, password)
      persistToken(session.access_token)
      try {
        setUser(await authApi.me())
      } catch (error) {
        persistToken(null)
        throw error
      }
    },
    [persistToken],
  )

  // Validate a token restored from a previous visit.
  useEffect(() => {
    if (tokenRef.current === null) {
      return
    }

    let cancelled = false
    authApi
      .me()
      .then((restored) => {
        if (!cancelled) setUser(restored)
      })
      .catch(() => {
        if (!cancelled) signOut()
      })
      .finally(() => {
        if (!cancelled) setIsRestoring(false)
      })

    return () => {
      cancelled = true
    }
  }, [signOut])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isRestoring,
      signIn,
      signOut,
    }),
    [user, isRestoring, signIn, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/** Reads the session. Throws when used outside the provider. */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (context === null) {
    throw new Error('useAuth debe usarse dentro de <AuthProvider>')
  }
  return context
}
