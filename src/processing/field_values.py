"""Pure helpers for compact Document Intelligence field values."""

from typing import Any


def first_typed_value(field: dict[str, Any]) -> Any:
    """Return the first non-null value from an Azure typed field."""
    return next(
        (
            value
            for key, value in field.items()
            if key.startswith("value") and value is not None
        ),
        None,
    )


def normalize_field_value(value: Any) -> Any:
    """Remove Azure wrappers and spatial metadata from a typed field value."""
    if isinstance(value, list):
        return [normalize_field_value(item) for item in value]
    if not isinstance(value, dict):
        return value
    typed_value = first_typed_value(value)
    if typed_value is not None:
        return normalize_field_value(typed_value)
    metadata = {"type", "content", "confidence", "boundingRegions", "spans"}
    return {
        key: normalize_field_value(item)
        for key, item in value.items()
        if key not in metadata
    }


def field_result(
    value: Any,
    content: Any = None,
    confidence: Any = None,
) -> dict[str, Any]:
    """Build the standard compact field result object."""
    return {"value": value, "content": content, "confidence": confidence}
