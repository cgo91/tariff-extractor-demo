/**
 * The settlement, laid out the way the pedimento prints it (RF-08).
 *
 * Amounts are right-aligned in tabular figures so the decimal points line up
 * and the column reads as a column, which is the whole point of a settlement:
 * the parts have to visibly add to the total.
 *
 * Two currencies meet in this table and the document has to say which is
 * which. The invoice is quoted in dollars; every contribution is settled in
 * pesos. The column header states the unit once, and the customs value shows
 * the conversion that produced it, so no figure is left to be inferred.
 */

import type { OperationDetails, Settlement } from '@/types/api'

const MXN = new Intl.NumberFormat('es-MX', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const USD = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

interface SettlementPanelProps {
  settlement: Settlement
  /** Invoice value and exchange rate the amounts were derived from. */
  details: OperationDetails
  /** IGI rate of the confirmed tariff item, as a fraction. */
  igiRate: number | null
}

export function SettlementPanel({ settlement, details, igiRate }: SettlementPanelProps) {
  const rows = [
    {
      concept: 'Valor en aduana · base gravable',
      // The only row whose amount is not a percentage of another: showing the
      // multiplication is what makes both currencies explicit.
      rate: `${USD.format(details.invoice_value_usd)} USD × ${details.exchange_rate.toFixed(4)}`,
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
        <caption className="sr-only">
          Contribuciones en pesos mexicanos, calculadas sobre una factura en dólares
          estadounidenses al tipo de cambio de la operación.
        </caption>
        <thead>
          <tr className="border-b border-rule bg-paper-sunk">
            <th className="field-label px-3 py-1.5 text-left">Concepto</th>
            <th className="field-label px-3 py-1.5 text-right">Tasa o cálculo</th>
            <th className="field-label px-3 py-1.5 text-right">Importe (MXN)</th>
          </tr>
        </thead>
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
