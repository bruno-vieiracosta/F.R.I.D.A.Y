from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from functools import total_ordering

from friday.shared.errors import ValidationError

MONEY_QUANTUM = Decimal("0.01")
MONEY_ROUNDING = ROUND_HALF_UP
PERCENTAGE_FACTOR = Decimal("100")
EXCHANGE_RATE_QUANTUM = Decimal("0.000001")


class InterestPeriod(StrEnum):
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


@dataclass(frozen=True, slots=True)
class Currency:
    code: str

    def __post_init__(self) -> None:
        code = self.code.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValidationError(
                "Currency code is invalid.",
                technical_message="Currency code must contain exactly 3 letters.",
                metadata={"code": self.code},
            )

        object.__setattr__(self, "code", code)

    def __str__(self) -> str:
        return self.code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code}


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        amount = _decimal_from(self.amount, "Money amount")
        _validate_currency(self.currency)
        object.__setattr__(self, "amount", quantize_money(amount))

    def __str__(self) -> str:
        return f"{self.currency.code} {self.amount}"

    def __add__(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._ensure_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, scalar: Decimal | int) -> Money:
        return Money(self.amount * _scalar_decimal(scalar), self.currency)

    def __rmul__(self, scalar: Decimal | int) -> Money:
        return self * scalar

    def __truediv__(self, scalar: Decimal | int) -> Money:
        divisor = _scalar_decimal(scalar)
        if divisor == Decimal("0"):
            raise ValidationError(
                "Money cannot be divided by zero.",
                technical_message="Attempted to divide Money by zero.",
            )
        return Money(self.amount / divisor, self.currency)

    def __lt__(self, other: Money) -> bool:
        self._ensure_same_currency(other)
        return self.amount < other.amount

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.currency == other.currency and self.amount == other.amount

    def _ensure_same_currency(self, other: Money) -> None:
        if not isinstance(other, Money):
            raise ValidationError(
                "Money operation requires another monetary value.",
                technical_message=f"Unsupported operand type: {type(other).__name__}.",
            )

        if self.currency != other.currency:
            raise ValidationError(
                "Money currencies are incompatible.",
                technical_message=(
                    "Cannot operate on monetary values with different currencies."
                ),
                metadata={
                    "left_currency": self.currency.code,
                    "right_currency": other.currency.code,
                },
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "amount": str(self.amount),
            "currency": self.currency.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class Percentage:
    value: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _decimal_from(self.value, "Percentage value"))

    def __str__(self) -> str:
        return f"{self.value}%"

    def to_factor(self) -> Decimal:
        return self.value / PERCENTAGE_FACTOR

    def to_dict(self) -> dict[str, str]:
        return {"value": str(self.value)}


@dataclass(frozen=True, slots=True)
class InterestRate:
    percentage: Percentage
    period: InterestPeriod

    def __post_init__(self) -> None:
        if not isinstance(self.percentage, Percentage):
            raise ValidationError("Interest rate percentage is invalid.")
        if not isinstance(self.period, InterestPeriod):
            raise ValidationError("Interest rate period is invalid.")

    def __str__(self) -> str:
        return f"{self.percentage} {self.period.value}"

    def to_dict(self) -> dict[str, object]:
        return {
            "percentage": self.percentage.to_dict(),
            "period": self.period.value,
        }


@dataclass(frozen=True, slots=True)
class ExchangeRate:
    source: Currency
    target: Currency
    rate: Decimal

    def __post_init__(self) -> None:
        _validate_currency(self.source)
        _validate_currency(self.target)
        if self.source == self.target:
            raise ValidationError(
                "Exchange rate currencies must be different.",
                technical_message="Source and target currencies are equal.",
                metadata={"currency": self.source.code},
            )

        rate = _decimal_from(self.rate, "Exchange rate")
        if rate <= Decimal("0"):
            raise ValidationError(
                "Exchange rate must be greater than zero.",
                technical_message="Exchange rate received a non-positive value.",
            )

        object.__setattr__(
            self,
            "rate",
            rate.quantize(EXCHANGE_RATE_QUANTUM, rounding=MONEY_ROUNDING),
        )

    def __str__(self) -> str:
        return f"{self.source.code}/{self.target.code} {self.rate}"

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "rate": str(self.rate),
        }


def quantize_money(value: Decimal) -> Decimal:
    amount = _decimal_from(value, "Money amount")
    return amount.quantize(MONEY_QUANTUM, rounding=MONEY_ROUNDING)


def _decimal_from(value: Decimal, name: str) -> Decimal:
    if not isinstance(value, Decimal):
        raise ValidationError(
            f"{name} must use Decimal.",
            technical_message=f"{name} received {type(value).__name__}.",
        )
    if not value.is_finite():
        raise ValidationError(
            f"{name} must be finite.",
            technical_message=f"{name} received a non-finite Decimal.",
        )
    return value


def _scalar_decimal(value: Decimal | int) -> Decimal:
    if isinstance(value, bool):
        raise ValidationError("Scalar must be numeric.")
    if isinstance(value, int):
        return Decimal(value)
    return _decimal_from(value, "Scalar")


def _validate_currency(value: Currency) -> None:
    if not isinstance(value, Currency):
        raise ValidationError("Currency is invalid.")
