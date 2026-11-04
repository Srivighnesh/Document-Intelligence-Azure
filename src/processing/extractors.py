"""Extract prompt text from Document Intelligence analyses."""

from typing import Any, Callable

from src.processing.field_values import (
    field_result,
    first_typed_value,
    normalize_field_value,
)
from src.processing.field_parser import ProfileFieldParser
from src.processing.profiles import Profile
from src.processing.text_select import compact, get_lines, select_relevant


LOW_CONFIDENCE_THRESHOLD = 0.6
FIELD_NAME_ALIASES = {"DocumentNumber": "CardNumber"}


def _allowed_fields(
    fields: dict[str, Any], allowed: set[str]
) -> dict[str, Any]:
    """Return model fields under the names exposed by the profile."""
    normalized = {
        name: field for name, field in fields.items() if name in allowed
    }
    for name, field in fields.items():
        canonical_name = FIELD_NAME_ALIASES.get(name)
        if canonical_name in allowed and canonical_name not in normalized:
            normalized[canonical_name] = field
    return normalized


def ocr_to_text(analysis: dict[str, Any], profile: Profile) -> str:
    """Extract selected OCR lines for a profile."""
    lines = get_lines(analysis)
    if profile.hints:
        lines = select_relevant(lines, profile.hints)
    return compact("\n".join(lines), profile.max_chars)


def fields_to_text(analysis: dict[str, Any], profile: Profile) -> str:
    """Extract allowlisted Document Intelligence fields."""
    rows: list[str] = []
    allowed = set(profile.fields)
    for document in analysis.get("documents", []):
        model_fields = document.get("fields", {})
        fields = (
            _allowed_fields(model_fields, allowed) if allowed else model_fields
        )
        for name, field in fields.items():
            value = field.get("content")
            if value is None:
                value = first_typed_value(field)
            if value is None:
                continue
            row = f"{name}: {value}"
            if (
                field.get("confidence") is not None
                and field["confidence"] < LOW_CONFIDENCE_THRESHOLD
            ):
                row += " (low confidence)"
            rows.append(row)
    if not rows:
        return ocr_to_text(analysis, profile)
    return compact("\n".join(rows), profile.max_chars)


def extract_result(analysis: dict[str, Any], profile: Profile) -> dict[str, Any]:
    """Return only allowlisted document fields with compact values."""
    fields: dict[str, dict[str, Any]] = {}
    allowed = set(profile.fields)
    for document in analysis.get("documents", []):
        model_fields = _allowed_fields(document.get("fields", {}), allowed)
        for name, field in model_fields.items():
            value = normalize_field_value(first_typed_value(field))
            fields[name] = field_result(
                value, field.get("content"), field.get("confidence")
            )
    if not fields and profile.fields:
        fields = ProfileFieldParser().parse(get_lines(analysis), profile)
    elif profile.model_id == "prebuilt-idDocument":
        parsed = ProfileFieldParser().parse(get_lines(analysis), profile)
        for name, fallback in parsed.items():
            if fields.get(name, {}).get("value") is None and fallback["value"]:
                fields[name] = fallback
    for name in profile.fields:
        fields.setdefault(name, field_result(None))
    return {"fields": fields}


EXTRACTORS: dict[str, Callable[[dict[str, Any], Profile], str]] = {
    "ocr": ocr_to_text,
    "fields": fields_to_text,
}
