"""FastAPI application for document upload and analysis."""

import logging
from functools import lru_cache

from fastapi import FastAPI, File, HTTPException, UploadFile

from src.processing.profiles import get_profile
from src.services.blob_storage import BlobStorageService
from src.services.document_intelligence import DocumentAnalyzer
from src.services.document_workflow import DocumentWorkflow
from src.services.foundry.client import FoundryClient

app = FastAPI(title="Document Intelligence and Foundry Workflow")
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/bmp",
}


@lru_cache(maxsize=1)
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
    foundry_agent = FoundryClient(
        project_endpoint=config.FOUNDRY_PROJECT_ENDPOINT,
        agent_name=config.FOUNDRY_AGENT_NAME,
        agent_version=config.FOUNDRY_AGENT_VERSION,
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
def analyze_document(
    file: UploadFile = File(...),
    model_id: str | None = None,
) -> dict:
    """Upload a document and return the Foundry agent response."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only PDF, JPEG, PNG, TIFF, and BMP files are supported.",
        )

    try:
        content = file.file.read(MAX_UPLOAD_BYTES + 1)
        if not content:
            raise HTTPException(status_code=400, detail="The file is empty.")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="The uploaded file must be 10 MB or smaller.",
            )
        if model_id is not None:
            get_profile(model_id)
        workflow = create_workflow()
        return workflow.process(
            filename=file.filename,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            model_id=model_id,
        )
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception:
        logger.exception("Document processing failed.")
        raise HTTPException(
            status_code=502,
            detail="Document processing failed.",
        )
