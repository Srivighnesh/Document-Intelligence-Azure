import json

import pytest

from src.services.document_workflow import (
    DocumentWorkflow,
    UnreadableDocumentError,
)


class FakeStorage:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, bytes, str]] = []
        self.blobs: dict[str, bytes] = {}

    def upload(self, blob_name: str, content: bytes, content_type: str) -> str:
        self.uploads.append((blob_name, content, content_type))
        self.blobs[blob_name] = content
        return f"https://storage/{blob_name}"

    def exists(self, blob_name: str) -> bool:
        return blob_name in self.blobs

    def download(self, blob_name: str) -> bytes:
        return self.blobs[blob_name]


class FakeAnalyzer:
    def __init__(self) -> None:
        self.calls = 0

    def analyze_bytes(self, content: bytes, model_id: str) -> dict:
        self.calls += 1
        assert content == b"pdf bytes"
        return {"documents": [{"fields": {"InvoiceId": {
            "valueString": "INV-1", "content": "INV-1", "confidence": 0.9
        }}}]}


class FakeAgent:
    def run(self, prompt: str) -> dict[str, str]:
        return {"summary": prompt}


def _workflow(agent=None):
    storage = FakeStorage()
    analyzer = FakeAnalyzer()
    workflow = DocumentWorkflow(
        storage=storage,
        document_analyzer=analyzer,
        model_id="prebuilt-invoice",
        foundry_agent=agent,
    )
    return workflow, storage, analyzer


def test_workflow_uploads_original_and_compact_result() -> None:
    workflow, storage, _ = _workflow()
    response = workflow.process("invoice.pdf", b"pdf bytes", "application/pdf")

    assert storage.uploads[0][0].startswith("uploads/")
    assert storage.uploads[0][1:] == (b"pdf bytes", "application/pdf")
    full_ocr_name, full_ocr_bytes, full_ocr_type = storage.uploads[1]
    assert full_ocr_name.startswith("full-ocr/")
    assert full_ocr_type == "application/json"
    full_ocr = json.loads(full_ocr_bytes)
    assert full_ocr["documents"][0]["fields"]["InvoiceId"]["valueString"] == "INV-1"

    result_name, result_bytes, content_type = storage.uploads[2]
    assert result_name.startswith("results/")
    assert content_type == "application/json"
    result = json.loads(result_bytes)
    assert result["fields"]["InvoiceId"] == {
        "value": "INV-1", "content": "INV-1", "confidence": 0.9
    }
    assert result["fields"]["VendorName"] == {
        "value": None, "content": None, "confidence": None
    }
    assert set(result) == {"fields", "fullOcrBlobName", "fullOcrBlobUrl"}
    assert set(response) == {
        "blobName", "blobUrl", "ocrBlobName", "ocrBlobUrl",
        "fullOcrBlobName", "fullOcrBlobUrl", "modelId", "duplicate",
    }
    assert response["ocrBlobName"] == result_name
    assert response["fullOcrBlobName"] == full_ocr_name
    result_payload = json.loads(result_bytes)
    assert result_payload["fullOcrBlobName"] == full_ocr_name
    assert result_payload["fullOcrBlobUrl"] == response["fullOcrBlobUrl"]
    assert response["modelId"] == "prebuilt-invoice"
    assert response["duplicate"] is False
    assert "summary" not in response


def test_workflow_adds_summary_when_agent_is_present() -> None:
    workflow, _, _ = _workflow(FakeAgent())

    response = workflow.process("invoice.pdf", b"pdf bytes", "application/pdf")

    assert response["summary"] == {"summary": "Summarize these invoice fields concisely:\nInvoiceId: INV-1"}


def test_workflow_reuses_cached_result_for_identical_content() -> None:
    workflow, storage, analyzer = _workflow()
    content = b"pdf bytes"

    first = workflow.process("first.pdf", content, "application/pdf")
    second = workflow.process("renamed.pdf", content, "application/pdf")

    assert analyzer.calls == 1
    assert len(storage.uploads) == 4  # source, full OCR, result, manifest
    assert first["blobName"] == second["blobName"]
    assert first["duplicate"] is False
    assert second["duplicate"] is True


def test_auto_mode_routes_by_content_not_filename() -> None:
    class AutoAnalyzer:
        def __init__(self) -> None:
            self.models: list[str] = []

        def analyze_bytes(self, content: bytes, model_id: str) -> dict:
            self.models.append(model_id)
            if model_id == "prebuilt-layout":
                label = (
                    "Invoice Number: INV-21"
                    if content == b"invoice bytes"
                    else "Passport Number: P12345; Date of Birth: 1990-01-01"
                )
                return {"pages": [{"lines": [{"content": label}]}]}
            if model_id == "prebuilt-invoice":
                return {"documents": [{"fields": {
                    "InvoiceId": {"valueString": "INV-21", "content": "INV-21"}
                }}]}
            return {"documents": [{"fields": {
                "DocumentNumber": {
                    "valueString": "P12345", "content": "P12345"
                }
            }}]}

    storage = FakeStorage()
    analyzer = AutoAnalyzer()
    workflow = DocumentWorkflow(storage, analyzer, "prebuilt-layout")

    invoice = workflow.process("same-name.pdf", b"invoice bytes", "application/pdf", "auto")
    identity = workflow.process("same-name.pdf", b"passport bytes", "application/pdf", "auto")

    assert invoice["modelId"] == "prebuilt-invoice"
    assert identity["modelId"] == "prebuilt-idDocument"
    assert invoice["duplicate"] is False
    assert identity["duplicate"] is False
    assert analyzer.models == [
        "prebuilt-layout",
        "prebuilt-invoice",
        "prebuilt-layout",
        "prebuilt-idDocument",
    ]


def test_auto_mode_reuses_cache_for_same_content_with_renamed_file() -> None:
    class AutoAnalyzer:
        def __init__(self) -> None:
            self.calls = 0

        def analyze_bytes(self, content: bytes, model_id: str) -> dict:
            self.calls += 1
            return {"pages": [{"lines": [{"content": "Invoice Number: INV-21"}]}]}

    analyzer = AutoAnalyzer()
    workflow = DocumentWorkflow(FakeStorage(), analyzer, "prebuilt-layout")

    first = workflow.process("one.pdf", b"same invoice", "application/pdf", "auto")
    second = workflow.process("renamed.pdf", b"same invoice", "application/pdf", "auto")

    assert analyzer.calls == 2  # one OCR pass plus one invoice-model pass
    assert first["modelId"] == "prebuilt-invoice"
    assert second["duplicate"] is True


def test_blank_document_is_rejected_before_any_blob_is_saved() -> None:
    class BlankAnalyzer:
        def analyze_bytes(self, content: bytes, model_id: str) -> dict:
            return {
                "pages": [{"lines": [{"content": "   "}]}],
                "documents": [{"fields": {}}],
            }

    storage = FakeStorage()
    workflow = DocumentWorkflow(storage, BlankAnalyzer(), "prebuilt-layout")

    with pytest.raises(UnreadableDocumentError, match="No readable text"):
        workflow.process("blank.pdf", b"blank pdf bytes", "application/pdf")

    assert storage.uploads == []
