/** Route guard: sends anonymous visitors to the login screen. */

import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'

export function ProtectedRoute() {
  const { isAuthenticated, isRestoring } = useAuth()
  const location = useLocation()

  // While a stored token is being validated, render nothing rather than
  // flashing the login screen at a user who is in fact signed in.
  if (isRestoring) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="eyebrow">Restaurando sesión</p>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/acceso" replace state={{ from: location.pathname }} />
  }

  return <Outlet />
}
