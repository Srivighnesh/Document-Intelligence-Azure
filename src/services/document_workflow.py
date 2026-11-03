"""Document upload, OCR, and Foundry orchestration."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from src.processing.extractors import extract_result
from src.processing.file_names import source_stem
from src.processing.profiles import get_profile
from src.services.blob_storage import BlobStorageService
from src.services.document_intelligence import DocumentAnalyzer

if TYPE_CHECKING:
    from src.services.foundry.client import FoundryClient

UPLOADS_PREFIX = "uploads"
RESULTS_PREFIX = "results"
JSON_CONTENT_TYPE = "application/json"


class DocumentWorkflow:
    """Run the complete document processing workflow."""

    def __init__(
        self,
        storage: BlobStorageService,
        document_analyzer: DocumentAnalyzer,
        model_id: str,
        foundry_agent: FoundryClient | None = None,
    ) -> None:
        """Store the service clients used by the workflow."""
        self.storage = storage
        self.document_analyzer = document_analyzer
        self.foundry_agent = foundry_agent
        self.model_id = model_id

    def process(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        model_id: str | None = None,
    ) -> dict[str, Any]:
        
        """Upload, analyze, and store the compact extraction result."""
        profile = get_profile(model_id or self.model_id)
        blob_name, blob_url = self._upload_source(filename, content, content_type)
        analysis = self.document_analyzer.analyze_bytes(
            content, profile.model_id
        )
        result = extract_result(analysis, profile)
        self._save_local_result(blob_name, result)
        ocr_blob_name, ocr_blob_url = self._upload_result(blob_name, result)
        response = {
            "blobName": blob_name,
            "blobUrl": blob_url,
            "ocrBlobName": ocr_blob_name,
            "ocrBlobUrl": ocr_blob_url,
            "modelId": profile.model_id,
        }
        if self.foundry_agent:
            from src.processing.summarize import run_agent

            response["summary"] = run_agent(analysis, profile, self.foundry_agent)
        return response

    def _upload_source(
        self, filename: str, content: bytes, content_type: str
    ) -> tuple[str, str]:
        """Upload the original document using a unique safe blob name."""
        safe_name = self._safe_blob_name(filename)
        blob_name = f"{UPLOADS_PREFIX}/{uuid4().hex}_{safe_name}"
        blob_url = self.storage.upload(blob_name, content, content_type)
        return blob_name, blob_url

    def _upload_result(
        self, blob_name: str, result: dict[str, Any]
    ) -> tuple[str, str]:
        """Upload the compact result JSON and return its name and URL."""
        result_name = self._ocr_blob_name(blob_name)
        content = json.dumps(result, ensure_ascii=False).encode("utf-8")
        result_url = self.storage.upload(result_name, content, JSON_CONTENT_TYPE)
        return result_name, result_url

    def _safe_blob_name(self, filename: str) -> str:
        """Prevent path traversal while preserving the uploaded filename."""
        safe_name = os.path.basename(filename).replace(" ", "_")
        return safe_name

    def _ocr_blob_name(self, blob_name: str) -> str:
        """Create the Blob name for the compact extraction result."""
        stem = source_stem(blob_name)
        return f"{RESULTS_PREFIX}/{stem}_ocr_result.json"

    def _save_local_result(
        self,
        blob_name: str,
        result: dict[str, Any],
    ) -> None:
        """Save the compact extraction result under data/results."""
        stem = source_stem(blob_name)
        result_directory = Path(__file__).resolve().parents[2] / "data" / "results"
        result_directory.mkdir(parents=True, exist_ok=True)
        output_path = result_directory / f"{stem}_ocr_result.json"
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
