/**
 * Operation history (RF-10). The table arrives in phase 4, once operations
 * can actually be created.
 */

export function HistoryPage() {
  return (
    <div className="space-y-8">
      <header>
        <p className="eyebrow">Registro</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">Historial</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">
          Aquí aparecerán las operaciones con su miniatura, nombre extraído,
          fracción, estado y fecha.
        </p>
      </header>

      <div className="border border-dashed border-rule-strong bg-paper-sunk px-6 py-10 text-center">
        <p className="text-sm text-ink-soft">
          Todavía no hay operaciones. Crea la primera desde «Nueva operación».
        </p>
      </div>
    </div>
  )
}
