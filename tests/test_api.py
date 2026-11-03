import base64

from fastapi.testclient import TestClient

from Backend import api


class FakeWorkflow:
    def process(self, filename, content, content_type, model_id):
        return {
            "filename": filename,
            "size": len(content),
            "contentType": content_type,
            "modelId": model_id,
        }


def _client(monkeypatch, max_bytes=10 * 1024 * 1024):
    monkeypatch.setattr(api, "create_workflow", lambda: FakeWorkflow())
    monkeypatch.setattr(api, "base64_document", api.Base64Document(max_bytes))
    return TestClient(api.app)


def test_analyze_accepts_valid_base64(monkeypatch) -> None:
    response = _client(monkeypatch).post("/documents/analyze", json={
        "filename": "doc.pdf", "contentType": "application/pdf",
        "contentBase64": base64.b64encode(b"pdf").decode(),
    })

    assert response.status_code == 200
    assert response.json()["size"] == 3


def test_analyze_rejects_invalid_base64(monkeypatch) -> None:
    response = _client(monkeypatch).post("/documents/analyze", json={
        "filename": "doc.pdf", "contentType": "application/pdf",
        "contentBase64": "bad!",
    })

    assert response.status_code == 400


def test_analyze_rejects_unsupported_content_type(monkeypatch) -> None:
    response = _client(monkeypatch).post("/documents/analyze", json={
        "filename": "doc.txt", "contentType": "text/plain",
        "contentBase64": "eA==",
    })

    assert response.status_code == 415


def test_analyze_rejects_oversized_content(monkeypatch) -> None:
    response = _client(monkeypatch, max_bytes=2).post("/documents/analyze", json={
        "filename": "doc.pdf", "contentType": "application/pdf",
        "contentBase64": base64.b64encode(b"abc").decode(),
    })

    assert response.status_code == 413


def test_analyze_accepts_model_id_as_query_parameter(monkeypatch) -> None:
    response = _client(monkeypatch).post(
        "/documents/analyze?modelId=prebuilt-invoice",
        json={
            "filename": "invoice.pdf",
            "contentType": "application/pdf",
            "contentBase64": "eA==",
        },
    )

    assert response.status_code == 200
    assert response.json()["modelId"] == "prebuilt-invoice"
