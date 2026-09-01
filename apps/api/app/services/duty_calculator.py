"""Contribution calculation (RF-08).

A pure service: no database, no storage, no network, no state. Everything it
needs arrives as arguments, which is what makes the three known cases in the
test suite meaningful.

Arithmetic runs in ``Decimal`` because binary floats cannot represent 0.008 or
0.16 exactly, and the pedimento has to add up to the cent.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.domain.models import Settlement

# Two decimals, rounded the way an invoice rounds.
CENTS = Decimal("0.01")


class DutyCalculator:
    """Computes the simplified contributions of an import operation.

        valor_aduana = valor_factura_usd x tipo_cambio
        IGI          = igi x valor_aduana
        DTA          = 0.008 x valor_aduana        (8 al millar)
        IVA          = 0.16 x (valor_aduana + IGI + DTA)
        total        = IGI + DTA + IVA

    Each amount is rounded to cents as it is produced, and every later amount
    derives from the already-rounded ones. That costs a fraction of a cent of
    precision and buys something worth more on a printed document: the figures
    shown add up exactly to the total shown.
    """

    # 8 al millar, per the Ley Federal de Derechos.
    DTA_RATE = Decimal("0.008")
    # General VAT rate.
    IVA_RATE = Decimal("0.16")

    def calculate(
        self,
        invoice_value_usd: float | Decimal,
        exchange_rate: float | Decimal,
        igi_rate: float | Decimal,
    ) -> Settlement:
        """Return the settlement for one operation.

        Args:
            invoice_value_usd: Invoice value in US dollars.
            exchange_rate: MXN per USD applied to the operation.
            igi_rate: Tariff rate of the chosen item, as a fraction (0.15 = 15 %).

        Raises:
            ValueError: when any input is negative, or the value or exchange
                rate is zero. Those are validated at the API boundary too; the
                check here keeps the service honest on its own.
        """
        value = _to_decimal(invoice_value_usd)
        rate = _to_decimal(exchange_rate)
        igi = _to_decimal(igi_rate)

        if value <= 0:
            raise ValueError("El valor de factura debe ser mayor que cero")
        if rate <= 0:
            raise ValueError("El tipo de cambio debe ser mayor que cero")
        if igi < 0:
            raise ValueError("La tasa de IGI no puede ser negativa")

        customs_value = _round(value * rate)
        igi_amount = _round(igi * customs_value)
        dta_amount = _round(self.DTA_RATE * customs_value)
        iva_amount = _round(self.IVA_RATE * (customs_value + igi_amount + dta_amount))
        total = _round(igi_amount + dta_amount + iva_amount)

        return Settlement(
            customs_value=float(customs_value),
            igi_amount=float(igi_amount),
            dta_amount=float(dta_amount),
            iva_amount=float(iva_amount),
            total=float(total),
        )


def _to_decimal(value: float | Decimal) -> Decimal:
    """Convert through ``str`` so 0.008 does not arrive as 0.00800000000000000017."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _round(amount: Decimal) -> Decimal:
    """Round to cents, half away from zero."""
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)
