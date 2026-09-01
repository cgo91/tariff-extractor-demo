/**
 * Sign-in screen (RF-01).
 *
 * The left panel is the thesis of the whole product: a photograph becomes a
 * tariff code becomes a pedimento. It is drawn with the same field boxes the
 * rest of the app uses, so the promise and the interface are the same object.
 */

import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'

import { ApiError } from '@/api/client'
import { useAuth } from '@/auth/AuthContext'
import { FieldInput } from '@/components/Field'

/** The four states an operation moves through, shown as the product promise. */
const PIPELINE = [
  { label: 'Fotografía', value: 'JPG · 10 MB' },
  { label: 'Extracción', value: 'Claude vision' },
  { label: 'Fracción · NICO', value: '8518.30.01 · 00' },
  { label: 'Pedimento', value: 'PDF · Anexo 22' },
]

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
    <main className="grid min-h-screen lg:grid-cols-[1.15fr_1fr]">
      {/* Left: the product thesis, drawn in the app's own vocabulary. */}
      <section className="relative flex flex-col justify-between bg-ink px-8 py-10 text-paper lg:px-14 lg:py-14">
        <p className="eyebrow text-paper/55">
          Sistema de apoyo a la clasificación arancelaria
        </p>

        <div className="my-12 max-w-xl lg:my-0">
          <h1 className="text-4xl leading-[1.08] font-semibold tracking-tight text-balance lg:text-5xl">
            De una fotografía del producto
            <br />
            <span className="text-paper/55">a la fracción, el NICO</span>
            <br />y el pedimento.
          </h1>

          <div className="mt-10 grid grid-cols-2 gap-px border border-paper/15 bg-paper/15 sm:grid-cols-4">
            {PIPELINE.map((step) => (
              <div key={step.label} className="bg-ink px-3 py-3">
                <span className="field-label text-paper/45">{step.label}</span>
                <span className="mt-0.5 block font-mono text-xs text-paper/85 tabular-nums">
                  {step.value}
                </span>
              </div>
            ))}
          </div>
        </div>

        <p className="max-w-md text-xs leading-relaxed text-paper/45">
          La clasificación es una propuesta asistida. La determinación final de la
          fracción y el NICO es responsabilidad del agente aduanal. Documento
          simulado con fines de demostración.
        </p>
      </section>

      {/* Right: the form. */}
      <section className="flex items-center justify-center px-6 py-16 lg:px-14">
        <div className="w-full max-w-sm">
          <p className="eyebrow">Acceso</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Inicia sesión</h2>
          <p className="mt-2 text-sm leading-relaxed text-ink-soft">
            Usa la cuenta creada por el script de carga inicial.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-3" noValidate>
            <FieldInput
              label="Correo electrónico"
              type="email"
              name="email"
              autoComplete="username"
              required
              value={email}
              placeholder="demo@aduana.mx"
              onChange={(event) => setEmail(event.target.value)}
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
            />

            {error ? (
              <div
                role="alert"
                className="border border-accent/35 bg-accent-wash px-3 py-2.5 text-sm text-accent-sunk"
              >
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              className="btn btn-primary w-full"
              disabled={isSubmitting || email.length === 0 || password.length === 0}
            >
              {isSubmitting ? 'Verificando…' : 'Entrar'}
            </button>
          </form>
        </div>
      </section>
    </main>
  )
}
