"""Pydantic models and JSON output handling for OCR results."""

import json
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OcrWord(BaseModel):
    """A word recognized by the OCR model."""

    content: str
    confidence: float | None = None


class OcrLine(BaseModel):
    """A line recognized by the OCR model."""

    content: str
    words: list[OcrWord] = Field(default_factory=list)


class OcrPage(BaseModel):
    """OCR text grouped by page."""

    page_number: int = Field(alias="pageNumber")
    width: float | None = None
    height: float | None = None
    unit: str | None = None
    lines: list[OcrLine] = Field(default_factory=list)


class OcrResult(BaseModel):
    """The compact JSON response written for one OCR analysis."""

    model_config = ConfigDict(populate_by_name=True)

    model_id: str = Field(alias="modelId")
    source: str
    content: str = ""
    pages: list[OcrPage] = Field(default_factory=list)


class ResultWriter:
    """Write compact OCR results to the result directory."""

    def __init__(self, result_directory: str | None = None) -> None:
        """Set the output directory, defaulting to data/results."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        self._result_directory = result_directory or os.path.join(
            project_root, "data", "results"
        )

    def write(
        self,
        analysis: dict[str, Any],
        source_name: str,
        model_id: str,
    ) -> str:
        """Extract OCR text and write it to a source-specific JSON file."""
        os.makedirs(self._result_directory, exist_ok=True)
        output_path = os.path.join(
            self._result_directory,
            f"{self._safe_name(source_name)}_ocr_result.json",
        )
        output = OcrResult(
            modelId=model_id,
            source=source_name,
            content=analysis.get("content", ""),
            pages=self._extract_pages(analysis),
        )
        with open(output_path, "w", encoding="utf-8") as result_file:
            json.dump(
                output.model_dump(mode="json", by_alias=True),
                result_file,
                indent=2,
                ensure_ascii=False,
            )
        return output_path

    def _extract_pages(self, analysis: dict[str, Any]) -> list[OcrPage]:
        """Keep OCR pages, lines, words, and confidence values."""
        pages = []
        for page in analysis.get("pages", []):
            page_words = page.get("words", [])
            lines = []
            for line in page.get("lines", []):
                line_spans = line.get("spans", [])
                words = [
                    OcrWord(
                        content=word.get("content", ""),
                        confidence=word.get("confidence"),
                    )
                    for word in page_words
                    if self._overlaps(word.get("span", {}), line_spans)
                ]
                lines.append(
                    OcrLine(content=line.get("content", ""), words=words)
                )
            pages.append(
                OcrPage(
                    pageNumber=page.get("pageNumber", 0),
                    width=page.get("width"),
                    height=page.get("height"),
                    unit=page.get("unit"),
                    lines=lines,
                )
            )
        return pages

    def _overlaps(self, word_span: dict[str, Any], line_spans: list[dict[str, Any]]) -> bool:
        """Check whether an OCR word belongs to one OCR line."""
        word_start = word_span.get("offset", 0)
        word_end = word_start + word_span.get("length", 0)
        return any(
            word_start < line_span.get("offset", 0) + line_span.get("length", 0)
            and line_span.get("offset", 0) < word_end
            for line_span in line_spans
        )

    def _safe_name(self, source_name: str) -> str:
        """Create a safe output filename from a URL or local path."""
        name = os.path.splitext(os.path.basename(source_name))[0]
        return "".join(
            character if character.isalnum() or character in ("-", "_") else "_"
            for character in name
        )
