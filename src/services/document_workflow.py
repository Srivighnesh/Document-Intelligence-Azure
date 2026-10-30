"""Document upload, OCR, and Foundry orchestration."""

import os
from typing import Any

from src.models.result_writer import ResultWriter
from src.services.blob_storage import BlobStorageService
from src.services.document_intelligence import DocumentAnalyzer
from src.services.foundry_agent import FoundryAgentClient

 
class DocumentWorkflow:
    """Run the complete document processing workflow."""

    def __init__(
        self,
        storage: BlobStorageService,
        document_analyzer: DocumentAnalyzer,
        foundry_agent: FoundryAgentClient,
        model_id: str,
    ) -> None:
        """Store the service clients used by the workflow."""
        self.storage = storage
        self.document_analyzer = document_analyzer
        self.foundry_agent = foundry_agent
        self.model_id = model_id
        self.result_writer = ResultWriter()

    def process(
        self,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        """Upload, analyze, summarize, and return structured results."""
        blob_name = self._safe_blob_name(filename)
        blob_url = self.storage.upload(blob_name, content, content_type)
        document_bytes = self.storage.download(blob_name)
        analysis = self.document_analyzer.analyze_bytes(
            document_bytes, self.model_id
        )
        ocr_path = self.result_writer.write(analysis, filename, self.model_id)
        agent_response = self.foundry_agent.analyze_ocr_file(ocr_path)
        return {
            "blobName": blob_name,
            "blobUrl": blob_url,
            "ocrResultPath": ocr_path,
            "agentResponse": agent_response,
        }

    def _safe_blob_name(self, filename: str) -> str:
        """Prevent path traversal while preserving the uploaded filename."""
        safe_name = os.path.basename(filename).replace(" ", "_")
        return f"{safe_name}"
