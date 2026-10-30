"""Azure Document Intelligence client wrapper."""

from typing import Any

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential


class DocumentAnalyzer:
    """Analyze documents using a deployed custom extraction model."""

    def __init__(self, endpoint: str, key: str) -> None:
        """Create a client using the Azure endpoint and API key."""
        self._client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
        )

    def analyze(self, document_source: str, model_id: str) -> dict[str, Any]:
        """Submit a local file or URL to the selected custom model."""
        request = self._build_request(document_source)
        return self._analyze_request(request, model_id)

    def analyze_bytes(self, content: bytes, model_id: str) -> dict[str, Any]:
        """Analyze document bytes received from Blob Storage."""
        request = AnalyzeDocumentRequest(bytes_source=content)
        return self._analyze_request(request, model_id)

    def _analyze_request(
        self, request: AnalyzeDocumentRequest, model_id: str
    ) -> dict[str, Any]:
        """Submit a request and convert the SDK result to a dictionary."""
        result = self._client.begin_analyze_document(model_id, request).result()
        return result.as_dict()

    def _build_request(self, document_source: str) -> AnalyzeDocumentRequest:
        """Build the SDK request body from a URL or local document."""
        if document_source.startswith(("http://", "https://")):
            return AnalyzeDocumentRequest(url_source=document_source)

        with open(document_source, "rb") as document_file:
            return AnalyzeDocumentRequest(bytes_source=document_file.read())
