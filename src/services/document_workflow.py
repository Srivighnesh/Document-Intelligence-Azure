"""Document upload, OCR, and Foundry orchestration."""

import json
import os
from typing import Any

from src.processing.profiles import get_profile
from src.processing.summarize import run_agent
from src.services.blob_storage import BlobStorageService
from src.services.document_intelligence import DocumentAnalyzer
from src.services.foundry.client import FoundryClient


class DocumentWorkflow:
    """Run the complete document processing workflow."""

    def __init__(
        self,
        storage: BlobStorageService,
        document_analyzer: DocumentAnalyzer,
        foundry_agent: FoundryClient,
        model_id: str,
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
        
        """Upload, analyze, summarize, and return structured results."""
        profile = get_profile(model_id or self.model_id)
        blob_name = self._safe_blob_name(filename)
        blob_url = self.storage.upload(blob_name, content, content_type)
        analysis = self.document_analyzer.analyze_bytes(
            content, profile.model_id
        )
        ocr_blob_name = self._ocr_blob_name(blob_name)
        ocr_blob_url = self.storage.upload(
            ocr_blob_name,
            json.dumps(analysis, ensure_ascii=False).encode("utf-8"),
            "application/json",
        )
        agent_response = run_agent(analysis, profile, self.foundry_agent)

        return {
            "blobName": blob_name,
            "blobUrl": blob_url,
            "ocrBlobName": ocr_blob_name,
            "ocrBlobUrl": ocr_blob_url,
            "modelId": profile.model_id,
            "summary": agent_response,
        }

    def _safe_blob_name(self, filename: str) -> str:
        """Prevent path traversal while preserving the uploaded filename."""
        safe_name = os.path.basename(filename).replace(" ", "_")
        return f"{safe_name}"

    def _ocr_blob_name(self, blob_name: str) -> str:
        """Create the Blob name for the raw OCR JSON result."""
        stem, _ = os.path.splitext(blob_name)
        return f"ocr/{stem}_ocr_result.json"
