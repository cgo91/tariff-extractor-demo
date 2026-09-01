/** Route table. Everything except the login screen sits behind the guard. */

import { Navigate, Route, Routes } from 'react-router-dom'

import { AuthProvider } from '@/auth/AuthContext'
import { ProtectedRoute } from '@/auth/ProtectedRoute'
import { AppLayout } from '@/components/AppLayout'
import { HistoryPage } from '@/pages/HistoryPage'
import { LoginPage } from '@/pages/LoginPage'
import { NewOperationPage } from '@/pages/NewOperationPage'

export function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/acceso" element={<LoginPage />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route path="/operaciones/nueva" element={<NewOperationPage />} />
            <Route path="/operaciones" element={<HistoryPage />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/operaciones/nueva" replace />} />
      </Routes>
    </AuthProvider>
  )
}
