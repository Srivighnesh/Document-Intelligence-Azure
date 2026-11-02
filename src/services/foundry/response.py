"""Helpers for parsing Foundry responses."""

import json
import re
from typing import Any


def parse_response(text: str) -> Any:
    """Parse JSON responses while preserving non-JSON text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return text
