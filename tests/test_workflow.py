import json

from src.processing.profiles import Profile
from src.services.document_workflow import DocumentWorkflow


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes, str]] = []

    def upload(self, blob_name: str, content: bytes, content_type: str) -> str:
        self.uploads.append((blob_name, content, content_type))
        return f"https://storage/{blob_name}"


class FakeAnalyzer:
    def analyze_bytes(self, content: bytes, model_id: str) -> dict:
        assert content == b"pdf bytes"
        return {"documents": [{"fields": {"InvoiceId": {
            "valueString": "INV-1", "content": "INV-1", "confidence": 0.9
        }}}]}


class FakeAgent:
    def run(self, prompt: str) -> dict[str, str]:
        return {"summary": prompt}


def _workflow(agent=None):
    storage = FakeStorage()
    workflow = DocumentWorkflow(
        storage=storage,
        document_analyzer=FakeAnalyzer(),
        model_id="prebuilt-invoice",
        foundry_agent=agent,
    )
    return workflow, storage


def test_workflow_uploads_original_and_compact_result() -> None:
    workflow, storage = _workflow()
    response = workflow.process("invoice.pdf", b"pdf bytes", "application/pdf")

    assert storage.uploads[0][0].startswith("uploads/")
    assert storage.uploads[0][1:] == (b"pdf bytes", "application/pdf")
    result_name, result_bytes, content_type = storage.uploads[1]
    assert result_name.startswith("results/")
    assert content_type == "application/json"
    result = json.loads(result_bytes)
    assert result["fields"]["InvoiceId"] == {
        "value": "INV-1", "content": "INV-1", "confidence": 0.9
    }
    assert result["fields"]["VendorName"] == {
        "value": None, "content": None, "confidence": None
    }
    assert set(result) == {"fields"}
    assert set(response) == {"blobName", "blobUrl", "ocrBlobName", "ocrBlobUrl", "modelId"}
    assert response["ocrBlobName"] == result_name
    assert response["modelId"] == "prebuilt-invoice"
    assert "summary" not in response


def test_workflow_adds_summary_when_agent_is_present() -> None:
    workflow, _ = _workflow(FakeAgent())

    response = workflow.process("invoice.pdf", b"pdf bytes", "application/pdf")

    assert response["summary"] == {"summary": "Summarize these invoice fields concisely:\nInvoiceId: INV-1"}
