/**
 * The settlement, laid out the way the pedimento prints it (RF-08).
 *
 * Amounts are right-aligned in tabular figures so the decimal points line up
 * and the column reads as a column, which is the whole point of a settlement:
 * the parts have to visibly add to the total.
 */

import type { Settlement } from '@/types/api'

const MXN = new Intl.NumberFormat('es-MX', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

interface SettlementPanelProps {
  settlement: Settlement
  /** IGI rate of the confirmed tariff item, as a fraction. */
  igiRate: number | null
}

export function SettlementPanel({ settlement, igiRate }: SettlementPanelProps) {
  const rows = [
    {
      concept: 'Valor en aduana',
      rate: 'base gravable',
      amount: settlement.customs_value,
    },
    {
      concept: 'IGI · Impuesto General de Importación',
      rate: igiRate === null ? '—' : `${(igiRate * 100).toFixed(0)} %`,
      amount: settlement.igi_amount,
    },
    {
      concept: 'DTA · Derecho de Trámite Aduanero',
      rate: '8 al millar',
      amount: settlement.dta_amount,
    },
    {
      concept: 'IVA · Impuesto al Valor Agregado',
      rate: '16 %',
      amount: settlement.iva_amount,
    },
  ]

  return (
    <section>
      <h2 className="text-lg font-semibold tracking-tight">Determinación de contribuciones</h2>

      <table className="mt-4 w-full border border-rule bg-white">
        <caption className="sr-only">Contribuciones calculadas en pesos mexicanos</caption>
        <tbody>
          {rows.map((row) => (
            <tr key={row.concept} className="border-b border-rule">
              <td className="px-3 py-2 text-sm">{row.concept}</td>
              <td className="px-3 py-2 text-right font-mono text-xs whitespace-nowrap text-ink-faint tabular-nums">
                {row.rate}
              </td>
              <td className="px-3 py-2 text-right font-mono text-sm whitespace-nowrap tabular-nums">
                {MXN.format(row.amount)}
              </td>
            </tr>
          ))}
          <tr>
            <td className="px-3 py-3 text-sm font-semibold">
              Total de contribuciones
              <span className="ml-1.5 text-xs font-normal text-ink-faint">MXN</span>
            </td>
            <td />
            <td className="px-3 py-3 text-right font-mono text-lg font-semibold whitespace-nowrap tabular-nums">
              {MXN.format(settlement.total)}
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  )
}
