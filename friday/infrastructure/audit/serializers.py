from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum

from friday.shared.clock import serialize_datetime
from friday.shared.errors import ValidationError
from friday.shared.identifiers import TypedId

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | list["JsonValue"] | dict[str, "JsonValue"]


def normalize_metadata(metadata: Mapping[str, object] | None) -> dict[str, JsonValue]:
    return {
        _normalize_key(key): _normalize_value(value)
        for key, value in (metadata or {}).items()
    }


def serialize_metadata(metadata: Mapping[str, object] | None) -> str:
    normalized = normalize_metadata(metadata)
    return json.dumps(
        normalized,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def deserialize_metadata(value: str) -> dict[str, JsonValue]:
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValidationError(
            "Audit metadata is invalid.",
            technical_message="Audit metadata is not valid JSON.",
            cause=error,
        ) from error

    if not isinstance(decoded, dict):
        raise ValidationError(
            "Audit metadata is invalid.",
            technical_message="Audit metadata JSON must be an object.",
        )

    return normalize_metadata(decoded)


def _normalize_key(key: object) -> str:
    if not isinstance(key, str) or not key.strip():
        raise ValidationError(
            "Audit metadata key is invalid.",
            technical_message="Audit metadata keys must be non-empty strings.",
        )
    return key


def _normalize_value(value: object) -> JsonValue:
    if value is None or isinstance(value, str | bool | int):
        return value

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValidationError(
                "Audit metadata value is invalid.",
                technical_message="Audit metadata floats must be finite.",
            )
        return value

    if isinstance(value, datetime):
        return serialize_datetime(value)

    if isinstance(value, TypedId):
        return str(value)

    if isinstance(value, Enum):
        return str(value.value)

    if isinstance(value, Mapping):
        return {
            _normalize_key(key): _normalize_value(nested_value)
            for key, nested_value in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalize_value(item) for item in value]

    raise ValidationError(
        "Audit metadata value is invalid.",
        technical_message="Audit metadata only accepts JSON-compatible values.",
        metadata={"value_type": type(value).__qualname__},
    )
