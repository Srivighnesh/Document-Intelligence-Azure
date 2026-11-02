"""Pure helpers for selecting and compacting OCR text."""

import re


def get_lines(ocr: dict) -> list[str]:
    """Return non-empty OCR lines in document order."""
    return [
        str(line["content"]).strip()
        for page in ocr.get("pages", [])
        for line in page.get("lines", [])
        if line.get("content")
    ]


def select_relevant(
    lines: list[str],
    hints: tuple[str, ...] | list[str],
    context: int = 2,
    fallback: int = 3,
) -> list[str]:
    """Select matching lines and following context without duplicates."""
    selected_indexes: set[int] = set()
    lowered_hints = tuple(hint.lower() for hint in hints)
    for index, line in enumerate(lines):
        if any(hint in line.lower() for hint in lowered_hints):
            selected_indexes.update(range(index, min(len(lines), index + context + 1)))
    if not selected_indexes:
        selected_indexes.update(range(min(len(lines), fallback)))
    return [lines[index] for index in sorted(selected_indexes)]


def compact(text: str, max_chars: int) -> str:
    """Normalize whitespace and cap text at a word boundary."""
    compact_text = re.sub(r"[ \t]+", " ", text)
    compact_text = re.sub(r"\n{3,}", "\n\n", compact_text).strip()
    if len(compact_text) > max_chars:
        candidate = compact_text[:max_chars]
        boundary = re.search(r"\s+\S*$", candidate)
        compact_text = (
            candidate[: boundary.start()].rstrip()
            if boundary
            else candidate
        )
    return compact_text
