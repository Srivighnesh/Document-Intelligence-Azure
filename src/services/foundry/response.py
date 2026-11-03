"""Helpers for parsing Foundry responses."""

import json
import re
from typing import Any

FENCE_PATTERN = r"^```(?:json)?\s*"
FENCE_END_PATTERN = r"\s*```$"


def parse_response(text: str) -> Any:
    """Parse JSON responses while preserving non-JSON text."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(FENCE_PATTERN, "", cleaned)
        cleaned = re.sub(FENCE_END_PATTERN, "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return text
