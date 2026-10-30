"""FastAPI application for document upload and analysis."""

import os

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.services.blob_storage import BlobStorageService
from src.services.document_intelligence import DocumentAnalyzer
from src.services.document_workflow import DocumentWorkflow
from src.services.foundry_agent import FoundryAgentClient

app = FastAPI(title="Document Intelligence and Foundry Workflow")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/bmp",
}


def create_workflow() -> DocumentWorkflow:
    """Create workflow clients from existing environment configuration."""
    from src import config

    storage = BlobStorageService(
        account_url=config.AZURE_STORAGE_ACCOUNT_URL,
        container_name=config.AZURE_STORAGE_CONTAINER_NAME,
    )
    document_analyzer = DocumentAnalyzer(
        endpoint=config.DOCUMENT_INTELLIGENCE_ENDPOINT,
        key=config.DOCUMENT_INTELLIGENCE_KEY,
    )
    foundry_agent = FoundryAgentClient(
        project_endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
        agent_name=config.FOUNDRY_AGENT_NAME,
        agent_version=config.FOUNDRY_AGENT_VERSION,
        max_ocr_chars=config.FOUNDRY_MAX_OCR_CHARS,
    )
    return DocumentWorkflow(
        storage=storage,
        document_analyzer=document_analyzer,
        foundry_agent=foundry_agent,
        model_id=config.DOCUMENT_INTELLIGENCE_MODEL_ID,
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Return a simple local liveness response."""
    return {"status": "ok"}


@app.post("/documents/analyze")
async def analyze_document(file: UploadFile = File(...)) -> dict:
    """Upload a document and return the Foundry agent response."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only PDF, JPEG, PNG, TIFF, and BMP files are supported.",
        )

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="The file is empty.")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="The uploaded file must be 10 MB or smaller.",
            )
        workflow = create_workflow()
        return workflow.process(
            filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Document workflow failed: {error}",
        ) from error
