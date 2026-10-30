"""Microsoft Foundry agent client for OCR post-processing."""

import json
import os
import re
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, Field


class FoundryAgentResult(BaseModel):
    """Persisted response from a Foundry agent."""

    project_endpoint: str = Field(alias="projectEndpoint")
    agent_name: str = Field(alias="agentName")
    agent_version: str | None = Field(default=None, alias="agentVersion")
    source: str
    response: Any


class FoundryAgentClient:
    """Send OCR text to a Microsoft Foundry agent."""

    FIELD_HINTS = {
        "companyName": ("corporation", "company name"),
        "commissionFileNumber": ("commission file number",),
        "reportingPeriodEndDate": ("period ended", "reporting period"),
        "incorporationState": ("state of incorporation", "incorporation"),
        "companyAddress": ("way, redmond", "street"),
        "telephoneNumber": ("telephone", "phone",),
        "tickerSymbols": ("trading symbol", "ticker",),
        "exchangeNames": ("name of exchange", "nasdaq", "nyse"),
    }

    def __init__(
        self,
        project_endpoint: str,
        agent_name: str,
        agent_version: str | None = None,
        max_ocr_chars: int = 1500,
        requested_fields: list[str] | None = None,
    ) -> None:
        """Create a Foundry client using the current Azure identity."""
        self.project_endpoint = project_endpoint
        self.agent_name = agent_name
        self.agent_version = agent_version
        if max_ocr_chars < 1:
            raise ValueError("max_ocr_chars must be greater than zero.")
        self.max_ocr_chars = max_ocr_chars
        self.requested_fields = requested_fields or [
            "companyName",
            "commissionFileNumber",
            "reportingPeriodEndDate",
            "incorporationState",
            "companyAddress",
            "telephoneNumber",
            "tickerSymbols",
            "exchangeNames",
        ]
        self._project = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential(),
        )
        self._openai = self._project.get_openai_client()

    def analyze_ocr_file(self, ocr_path: str) -> Any:
        """Read an OCR JSON file and ask the configured agent to analyze it."""
        with open(ocr_path, encoding="utf-8") as ocr_file:
            ocr_result: dict[str, Any] = json.load(ocr_file)

        return self.analyze_ocr_result(ocr_result)

    def analyze_ocr_result(self, ocr_result: dict[str, Any]) -> Any:
        """Send an in-memory OCR result to the configured agent."""
        ocr_text = self._extract_relevant_text(ocr_result)
        prompt = f"Summarize this document text concisely:\n{ocr_text}"
        response = self._openai.responses.create(
            input=prompt,
            extra_body={
                "agent_reference": {
                    "type": "agent_reference",
                    "name": self.agent_name,
                    **({"version": self.agent_version} if self.agent_version else {}),
                }
            },
        )
        return self._parse_response(response.output_text)

    def _parse_response(self, response_text: str) -> Any:
        """Parse JSON output while preserving a useful fallback response."""
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return response_text

    def _extract_relevant_text(self, ocr_result: dict[str, Any]) -> str:
        """Select only OCR lines related to the requested fields."""
        lines = [
            str(line.get("content", "")).strip()
            for page in ocr_result.get("pages", [])
            for line in page.get("lines", [])
            if line.get("content")
        ]
        selected_indexes: set[int] = set()
        for field in self.requested_fields:
            hints = self.FIELD_HINTS.get(
                field, (self._field_label(field),)
            )
            for index, line in enumerate(lines):
                if any(hint in line.lower() for hint in hints):
                    selected_indexes.update(
                        range(index, min(len(lines), index + 3))
                    )

        selected_lines = []
        seen_lines: set[str] = set()
        for index in sorted(selected_indexes):
            line = lines[index]
            if line not in seen_lines:
                selected_lines.append(line)
                seen_lines.add(line)
        if not selected_lines:
            selected_lines = lines[:3]
        return self._compact_text("\n".join(selected_lines))

    def _field_label(self, field: str) -> str:
        """Convert a camel-case field name to searchable text."""
        return re.sub(r"(?<!^)([A-Z])", r" \1", field).lower()

    def _compact_text(self, text: str) -> str:
        """Normalize selected OCR text and cap it before sending."""
        compact_text = re.sub(r"[ \t]+", " ", text)
        compact_text = re.sub(r"\n{3,}", "\n\n", compact_text).strip()
        if len(compact_text) > self.max_ocr_chars:
            compact_text = compact_text[: self.max_ocr_chars].rsplit(" ", 1)[0]
        return compact_text

    def save_response(self, response: str, source_name: str) -> str:
        """Save the agent response beside the OCR result."""
        result_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "results",
        )
        os.makedirs(result_directory, exist_ok=True)
        output = FoundryAgentResult(
            projectEndpoint=self.project_endpoint,
            agentName=self.agent_name,
            agentVersion=self.agent_version,
            source=source_name,
            response=response,
        )
        output_path = os.path.join(
            result_directory,
            f"{os.path.splitext(os.path.basename(source_name))[0]}_foundry_result.json",
        )
        with open(output_path, "w", encoding="utf-8") as output_file:
            json.dump(
                output.model_dump(mode="json", by_alias=True),
                output_file,
                indent=2,
                ensure_ascii=False,
            )
        return output_path
