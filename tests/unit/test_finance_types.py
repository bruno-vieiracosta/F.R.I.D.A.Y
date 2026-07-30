from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from friday.shared.errors import ValidationError
from friday.shared.finance import (
    MONEY_QUANTUM,
    MONEY_ROUNDING,
    Currency,
    ExchangeRate,
    InterestPeriod,
    InterestRate,
    Money,
    Percentage,
    quantize_money,
)
from friday.shared.types import Result

BRL = Currency("BRL")
USD = Currency("USD")


@pytest.mark.unit
def test_currency_normalizes_and_serializes_code() -> None:
    currency = Currency(" brl ")

    assert currency.code == "BRL"
    assert str(currency) == "BRL"
    assert currency.to_dict() == {"code": "BRL"}
    assert currency == Currency("BRL")


@pytest.mark.unit
def test_currency_validates_code() -> None:
    with pytest.raises(ValidationError, match="Currency code is invalid"):
        Currency("BR")

    with pytest.raises(ValidationError, match="Currency code is invalid"):
        Currency("12$")


@pytest.mark.unit
def test_money_is_immutable_and_serializable() -> None:
    money = Money(Decimal("10"), BRL)

    with pytest.raises(FrozenInstanceError):
        money.amount = Decimal("20")

    assert str(money) == "BRL 10.00"
    assert money.to_dict() == {
        "amount": "10.00",
        "currency": {"code": "BRL"},
    }


@pytest.mark.unit
def test_money_requires_decimal_amount() -> None:
    with pytest.raises(ValidationError, match="Money amount must use Decimal"):
        Money("10", BRL)


@pytest.mark.unit
def test_money_rounding_uses_single_strategy() -> None:
    assert Decimal("0.01") == MONEY_QUANTUM
    assert MONEY_ROUNDING == "ROUND_HALF_UP"
    assert quantize_money(Decimal("10.005")) == Decimal("10.01")
    assert Money(Decimal("10.004"), BRL).amount == Decimal("10.00")


@pytest.mark.unit
def test_money_addition_and_subtraction_require_same_currency() -> None:
    assert Money(Decimal("10"), BRL) + Money(Decimal("2.50"), BRL) == Money(
        Decimal("12.50"),
        BRL,
    )
    assert Money(Decimal("10"), BRL) - Money(Decimal("2.50"), BRL) == Money(
        Decimal("7.50"),
        BRL,
    )

    with pytest.raises(ValidationError, match="currencies are incompatible"):
        _ = Money(Decimal("10"), BRL) + Money(Decimal("1"), USD)


@pytest.mark.unit
def test_money_scalar_operations() -> None:
    money = Money(Decimal("10"), BRL)

    assert money * Decimal("1.5") == Money(Decimal("15.00"), BRL)
    assert Decimal("1.5") * money == Money(Decimal("15.00"), BRL)
    assert money * 2 == Money(Decimal("20.00"), BRL)
    assert money / Decimal("4") == Money(Decimal("2.50"), BRL)

    with pytest.raises(ValidationError, match="divided by zero"):
        _ = money / Decimal("0")


@pytest.mark.unit
def test_money_rejects_invalid_scalar() -> None:
    with pytest.raises(ValidationError, match="Scalar must be numeric"):
        _ = Money(Decimal("10"), BRL) * True

    with pytest.raises(ValidationError, match="Scalar must use Decimal"):
        _ = Money(Decimal("10"), BRL) * "2"


@pytest.mark.unit
def test_money_comparison_requires_same_currency() -> None:
    assert Money(Decimal("10"), BRL) > Money(Decimal("9.99"), BRL)
    assert Money(Decimal("10"), BRL) >= Money(Decimal("10"), BRL)
    assert Money(Decimal("9.99"), BRL) < Money(Decimal("10"), BRL)

    with pytest.raises(ValidationError, match="currencies are incompatible"):
        _ = Money(Decimal("10"), BRL) > Money(Decimal("10"), USD)


@pytest.mark.unit
def test_percentage_exposes_decimal_factor_and_serialization() -> None:
    percentage = Percentage(Decimal("12.5"))

    assert str(percentage) == "12.5%"
    assert percentage.to_factor() == Decimal("0.125")
    assert percentage.to_dict() == {"value": "12.5"}


@pytest.mark.unit
def test_percentage_requires_decimal() -> None:
    with pytest.raises(ValidationError, match="Percentage value must use Decimal"):
        Percentage("10")


@pytest.mark.unit
def test_interest_rate_serializes_percentage_and_period() -> None:
    rate = InterestRate(Percentage(Decimal("1.25")), InterestPeriod.MONTHLY)

    assert str(rate) == "1.25% MONTHLY"
    assert rate.to_dict() == {
        "percentage": {"value": "1.25"},
        "period": "MONTHLY",
    }


@pytest.mark.unit
def test_interest_rate_validates_components() -> None:
    with pytest.raises(ValidationError, match="percentage is invalid"):
        InterestRate("1.0", InterestPeriod.MONTHLY)

    with pytest.raises(ValidationError, match="period is invalid"):
        InterestRate(Percentage(Decimal("1.0")), "MONTHLY")


@pytest.mark.unit
def test_exchange_rate_validates_and_serializes() -> None:
    rate = ExchangeRate(BRL, USD, Decimal("0.20123456"))

    assert str(rate) == "BRL/USD 0.201235"
    assert rate.to_dict() == {
        "source": {"code": "BRL"},
        "target": {"code": "USD"},
        "rate": "0.201235",
    }


@pytest.mark.unit
def test_exchange_rate_rejects_invalid_values() -> None:
    with pytest.raises(ValidationError, match="must be different"):
        ExchangeRate(BRL, BRL, Decimal("1"))

    with pytest.raises(ValidationError, match="greater than zero"):
        ExchangeRate(BRL, USD, Decimal("0"))

    with pytest.raises(ValidationError, match="Exchange rate must use Decimal"):
        ExchangeRate(BRL, USD, "0.20")


@pytest.mark.unit
def test_financial_types_integrate_with_result_and_errors() -> None:
    success: Result[Money, ValidationError] = Result.success(Money(Decimal("10"), BRL))
    failure: Result[Money, ValidationError] = Result.failure(
        ValidationError("Currency mismatch."),
    )

    assert success.map(lambda money: money * Decimal("2")).value == Money(
        Decimal("20"),
        BRL,
    )
    assert failure.to_dict() == {
        "success": False,
        "error": {
            "code": "FRIDAY-VALIDATION-001",
            "category": "VALIDATION",
            "message": "Currency mismatch.",
        },
    }
