"""Tests for the contribution calculation (RF-08).

The three named cases are worked by hand in the docstrings, so a future change
to the formula has to disagree with arithmetic, not with a fixture.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.duty_calculator import DutyCalculator


@pytest.fixture
def calculator() -> DutyCalculator:
    return DutyCalculator()


class TestKnownCases:
    def test_headphones_at_15_percent(self, calculator: DutyCalculator) -> None:
        """100 USD at 17.50, IGI 15 %.

        valor_aduana = 100 x 17.50            = 1750.00
        IGI          = 0.15 x 1750.00         =  262.50
        DTA          = 0.008 x 1750.00        =   14.00
        IVA          = 0.16 x 2026.50         =  324.24
        total        = 262.50 + 14.00 + 324.24 = 600.74
        """
        settlement = calculator.calculate(100.0, 17.50, 0.15)

        assert settlement.customs_value == 1750.00
        assert settlement.igi_amount == 262.50
        assert settlement.dta_amount == 14.00
        assert settlement.iva_amount == 324.24
        assert settlement.total == 600.74

    def test_duty_free_smartphone(self, calculator: DutyCalculator) -> None:
        """1000 USD at 18.00, IGI 0 % (heading 8517 is duty free).

        valor_aduana = 1000 x 18.00           = 18000.00
        IGI          = 0.00 x 18000.00        =     0.00
        DTA          = 0.008 x 18000.00       =   144.00
        IVA          = 0.16 x 18144.00        =  2903.04
        total        = 0.00 + 144.00 + 2903.04 = 3047.04
        """
        settlement = calculator.calculate(1000.0, 18.00, 0.0)

        assert settlement.customs_value == 18000.00
        assert settlement.igi_amount == 0.00
        assert settlement.dta_amount == 144.00
        assert settlement.iva_amount == 2903.04
        assert settlement.total == 3047.04

    def test_rounding_at_every_step(self, calculator: DutyCalculator) -> None:
        """99.99 USD at 17.33, IGI 5 % — every intermediate needs rounding.

        valor_aduana = 99.99 x 17.33 = 1732.8267  -> 1732.83
        IGI          = 0.05 x 1732.83 =   86.6415 ->   86.64
        DTA          = 0.008 x 1732.83 =  13.86264 ->  13.86
        IVA          = 0.16 x 1833.33 =  293.3328 ->  293.33
        total        = 86.64 + 13.86 + 293.33     =  393.83
        """
        settlement = calculator.calculate(99.99, 17.33, 0.05)

        assert settlement.customs_value == 1732.83
        assert settlement.igi_amount == 86.64
        assert settlement.dta_amount == 13.86
        assert settlement.iva_amount == 293.33
        assert settlement.total == 393.83


class TestInternalConsistency:
    @pytest.mark.parametrize(
        ("value", "rate", "igi"),
        [
            (100.0, 17.50, 0.15),
            (1000.0, 18.00, 0.0),
            (99.99, 17.33, 0.05),
            (1234.56, 17.8912, 0.10),
            (0.01, 20.00, 0.20),
            (999999.99, 17.00, 0.15),
        ],
    )
    def test_the_printed_figures_add_up_to_the_printed_total(
        self, calculator: DutyCalculator, value: float, rate: float, igi: float
    ) -> None:
        """What the pedimento shows must sum to what it says the total is."""
        settlement = calculator.calculate(value, rate, igi)

        parts = (
            Decimal(str(settlement.igi_amount))
            + Decimal(str(settlement.dta_amount))
            + Decimal(str(settlement.iva_amount))
        )
        assert parts == Decimal(str(settlement.total))

    @pytest.mark.parametrize(
        ("value", "rate", "igi"),
        [(100.0, 17.50, 0.15), (2500.0, 17.10, 0.0), (49.95, 19.99, 0.20)],
    )
    def test_every_amount_has_at_most_two_decimals(
        self, calculator: DutyCalculator, value: float, rate: float, igi: float
    ) -> None:
        settlement = calculator.calculate(value, rate, igi)

        for amount in settlement.model_dump().values():
            assert Decimal(str(amount)).as_tuple().exponent >= -2


class TestPrecision:
    def test_uses_decimal_rather_than_binary_floats(
        self, calculator: DutyCalculator
    ) -> None:
        """0.1 + 0.2 style drift must not reach the document."""
        settlement = calculator.calculate(0.1, 3.0, 0.0)

        assert settlement.customs_value == 0.30

    def test_accepts_decimal_inputs(self, calculator: DutyCalculator) -> None:
        settlement = calculator.calculate(
            Decimal("100"), Decimal("17.50"), Decimal("0.15")
        )

        assert settlement.total == 600.74


class TestRejectedInputs:
    @pytest.mark.parametrize("value", [0.0, -1.0])
    def test_rejects_a_non_positive_invoice_value(
        self, calculator: DutyCalculator, value: float
    ) -> None:
        with pytest.raises(ValueError, match="valor de factura"):
            calculator.calculate(value, 17.50, 0.15)

    @pytest.mark.parametrize("rate", [0.0, -17.50])
    def test_rejects_a_non_positive_exchange_rate(
        self, calculator: DutyCalculator, rate: float
    ) -> None:
        with pytest.raises(ValueError, match="tipo de cambio"):
            calculator.calculate(100.0, rate, 0.15)

    def test_rejects_a_negative_igi_rate(self, calculator: DutyCalculator) -> None:
        with pytest.raises(ValueError, match="IGI"):
            calculator.calculate(100.0, 17.50, -0.15)
