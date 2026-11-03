"""FastAPI application for document upload and analysis."""

import logging
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from src.processing.base64_document import (
    Base64Document,
    DEFAULT_MAX_BYTES,
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidBase64Error,
)
from src.processing.profiles import get_profile
from src.services.blob_storage import BlobStorageService
from src.services.document_intelligence import DocumentAnalyzer
from src.services.document_workflow import DocumentWorkflow

app = FastAPI(title="Document Intelligence and Foundry Workflow")
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = DEFAULT_MAX_BYTES
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/bmp",
}
base64_document = Base64Document(MAX_UPLOAD_BYTES)


class AnalyzeRequest(BaseModel):
    """JSON request containing a Base64 encoded document."""

    model_config = ConfigDict(populate_by_name=True)
    filename: str
    content_type: str = Field(alias="contentType")
    content_base64: str = Field(alias="contentBase64")
    model_id: str | None = Field(default=None, alias="modelId")


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
    foundry_agent = None
    if config.FOUNDRY_ENABLED:
        from src.services.foundry.client import FoundryClient

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
    request: AnalyzeRequest,
    model_id: str | None = Query(default=None, alias="modelId"),
) -> dict:
    """Decode a JSON upload and return analysis metadata."""
    selected_model_id = model_id or request.model_id
    if not request.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    if request.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Only PDF, JPEG, PNG, TIFF, and BMP files are supported.",
        )

    try:
        content = _decode_content(request.content_base64)
        if selected_model_id is not None:
            get_profile(selected_model_id)
        workflow = create_workflow()
        return workflow.process(
            filename=request.filename,
            content=content,
            content_type=request.content_type,
            model_id=selected_model_id,
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


def _decode_content(value: str) -> bytes:
    """Decode request Base64 and map document errors to HTTP responses."""
    try:
        return base64_document.decode(value)
    except InvalidBase64Error as error:
        raise HTTPException(
            status_code=400, detail="Invalid Base64 content."
        ) from error
    except EmptyDocumentError as error:
        raise HTTPException(status_code=400, detail="The file is empty.") from error
    except DocumentTooLargeError as error:
        raise HTTPException(
            status_code=413,
            detail="The uploaded file must be 10 MB or smaller.",
        ) from error
