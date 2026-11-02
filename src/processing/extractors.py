"""Extract prompt text from Document Intelligence analyses."""

from typing import Any, Callable

from src.processing.profiles import Profile
from src.processing.text_select import compact, get_lines, select_relevant


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
        for name, field in document.get("fields", {}).items():
            if allowed and name not in allowed:
                continue
            value = field.get("content")
            if value is None:
                value = next(
                    (
                        field[key]
                        for key in field
                        if key.startswith("value") and field[key] is not None
                    ),
                    None,
                )
            if value is None:
                continue
            row = f"{name}: {value}"
            if field.get("confidence") is not None and field["confidence"] < 0.6:
                row += " (low confidence)"
            rows.append(row)
    if not rows:
        return ocr_to_text(analysis, profile)
    return compact("\n".join(rows), profile.max_chars)


EXTRACTORS: dict[str, Callable[[dict[str, Any], Profile], str]] = {
    "ocr": ocr_to_text,
    "fields": fields_to_text,
}
