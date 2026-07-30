from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from friday.shared.errors import ValidationError

SECRET_IDENTIFIER_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
REDACTED_SECRET_VALUE = "<redacted>"


class SecretSource(StrEnum):
    ENVIRONMENT = "environment"
    FILE = "file"
    RESOLVER = "resolver"


@dataclass(frozen=True, slots=True)
class SecretIdentifier:
    name: str

    def __post_init__(self) -> None:
        normalized = self.name.strip()
        if not normalized:
            raise ValidationError(
                "Secret identifier is invalid.",
                technical_message="Secret identifiers must not be empty.",
            )

        if "\x00" in normalized:
            raise ValidationError(
                "Secret identifier is invalid.",
                technical_message="Secret identifiers must not contain null bytes.",
            )

        if SECRET_IDENTIFIER_PATTERN.fullmatch(normalized) is None:
            raise ValidationError(
                "Secret identifier is invalid.",
                technical_message=(
                    "Secret identifiers must use uppercase letters, digits and "
                    "underscores, starting with a letter."
                ),
            )

        object.__setattr__(self, "name", normalized)

    @classmethod
    def from_text(cls, value: str) -> SecretIdentifier:
        return cls(value)

    def __str__(self) -> str:
        return self.name

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name}


@dataclass(frozen=True, slots=True)
class Secret:
    identifier: SecretIdentifier
    source: SecretSource
    _value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not self._value:
            raise ValidationError(
                "Secret value is invalid.",
                technical_message="Secret values must not be empty.",
            )

    def reveal(self) -> str:
        return self._value

    def __str__(self) -> str:
        return REDACTED_SECRET_VALUE

    def to_dict(self) -> dict[str, str]:
        return {
            "identifier": str(self.identifier),
            "source": self.source.value,
            "value": REDACTED_SECRET_VALUE,
        }
