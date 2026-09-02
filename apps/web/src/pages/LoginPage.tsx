/**
 * Sign-in screen (RF-01).
 *
 * A single centred card on a sunk ground. The card lifts off the page the way
 * the design system asks for depth — a change of ground plus a hairline rule,
 * never a drop shadow — and carries a ruled header, so it reads as a block of
 * the document the app produces rather than a generic panel.
 *
 * A login authenticates; it does not pitch the product, so the promise is one
 * line under the title and the legal notice sits outside the card, where fine
 * print belongs.
 */

import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { ApiError } from '@/api/client'
import { useAuth } from '@/auth/AuthContext'
import { FieldInput } from '@/components/Field'

export function LoginPage() {
  const { isAuthenticated, isRestoring, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isRestoring && isAuthenticated) {
    const from = (location.state as { from?: string } | null)?.from
    return <Navigate to={from ?? '/operaciones/nueva'} replace />
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await signIn(email, password)
      navigate('/operaciones/nueva', { replace: true })
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'No se pudo conectar con el servidor. Revisa que la API esté levantada.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-paper-sunk px-6 py-12">
      <div className="w-full max-w-md">
        <div className="border border-rule bg-white">
          {/* The same mark the authenticated header carries. */}
          <div className="flex items-baseline gap-3 border-b border-rule px-7 py-4">
            <span className="font-mono text-sm font-semibold tracking-tight">
              8518.30.01
            </span>
            <span className="eyebrow">Clasificación arancelaria</span>
          </div>

          <div className="px-7 pt-7 pb-8">
            <h1 className="text-2xl font-semibold tracking-tight">Inicia sesión</h1>
            <p className="mt-2 text-sm leading-relaxed text-ink-soft">
              De una fotografía del producto a la fracción, el NICO y el pedimento.
            </p>

            <form onSubmit={handleSubmit} className="mt-7" noValidate>
              {/* Adjacent boxes collapse their shared rule, as on the pedimento. */}
              <FieldInput
                label="Correo electrónico"
                type="email"
                name="email"
                autoComplete="username"
                required
                value={email}
                placeholder="demo@aduana.mx"
                onChange={(event) => setEmail(event.target.value)}
                className="relative focus-within:z-10"
              />
              <FieldInput
                label="Contraseña"
                type="password"
                name="password"
                autoComplete="current-password"
                required
                value={password}
                placeholder="••••••••"
                onChange={(event) => setPassword(event.target.value)}
                className="relative -mt-px focus-within:z-10"
              />

              {error ? (
                <div
                  role="alert"
                  className="mt-3 border border-accent/35 bg-accent-wash px-3 py-2.5 text-sm text-accent-sunk"
                >
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                className="btn btn-primary mt-4 w-full"
                disabled={isSubmitting || email.length === 0 || password.length === 0}
              >
                {isSubmitting ? 'Verificando…' : 'Entrar'}
              </button>

              <p className="mt-3 text-xs leading-relaxed text-ink-soft">
                Usa la cuenta creada por el script de carga inicial.
              </p>
            </form>
          </div>
        </div>

        <p className="mt-5 text-xs leading-relaxed text-ink-faint">
          Documento simulado con fines de demostración. La determinación final de
          la fracción arancelaria y el NICO es responsabilidad del agente aduanal.
        </p>
      </div>
    </main>
  )
}
