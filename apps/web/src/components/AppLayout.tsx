/**
 * Shell for every authenticated screen: a ruled header, the navigation, and
 * the standing disclaimer that the pedimento produced here is simulated.
 */

import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '@/auth/AuthContext'

const NAV_ITEMS = [
  { to: '/operaciones/nueva', label: 'Nueva operación' },
  { to: '/operaciones', label: 'Historial' },
]

export function AppLayout() {
  const { user, signOut } = useAuth()

  return (
    <div className="min-h-screen">
      <header className="border-b border-rule bg-paper">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-4">
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-sm font-semibold tracking-tight">
              8518.30.01
            </span>
            <span className="eyebrow hidden sm:inline">
              Clasificación arancelaria
            </span>
          </div>

          <nav className="flex items-center gap-1" aria-label="Secciones">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/operaciones'}
                className={({ isActive }) =>
                  [
                    'px-3 py-1.5 text-sm transition-colors',
                    isActive
                      ? 'border-b-2 border-accent font-semibold text-ink'
                      : 'border-b-2 border-transparent text-ink-soft hover:text-ink',
                  ].join(' ')
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-4">
            <span className="hidden font-mono text-xs text-ink-faint md:inline">
              {user?.email}
            </span>
            <button type="button" onClick={signOut} className="btn btn-secondary py-1.5">
              Salir
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-10">
        <Outlet />
      </main>

      <footer className="border-t border-rule">
        <p className="mx-auto max-w-6xl px-6 py-5 text-xs text-ink-faint">
          Documento simulado con fines de demostración. La determinación final de
          la fracción arancelaria y el NICO es responsabilidad del agente aduanal.
        </p>
      </footer>
    </div>
  )
}
