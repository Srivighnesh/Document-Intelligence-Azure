"""Document upload, OCR, and Foundry orchestration."""

from __future__ import annotations
import time
import hashlib
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

from src.processing.document_classifier import (
    CLASSIFIER_VERSION,
    classify_document,
)
from src.processing.extractors import extract_result
from src.processing.profiles import PROFILES, Profile, get_profile
from src.processing.text_select import get_lines
from src.services.blob_storage import BlobStorageService
from src.services.document_intelligence import DocumentAnalyzer

if TYPE_CHECKING:
    from src.services.foundry.client import FoundryClient



UPLOADS_PREFIX = "uploads"
RESULTS_PREFIX = "results"
MANIFESTS_PREFIX = "manifests"
FULL_OCR_PREFIX = "full-ocr"
JSON_CONTENT_TYPE = "application/json"
CACHE_SCHEMA_VERSION = 1


class UnreadableDocumentError(ValueError):
    """OCR and extraction found no readable document content."""


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
        
        """Upload and analyze a document, reusing completed duplicate results."""
        start_time = time.perf_counter()
        
        requested_model_id = model_id or self.model_id
        auto_detect = requested_model_id.casefold() == "auto"
        profile = None if auto_detect else get_profile(requested_model_id)
        content_hash = hashlib.sha256(content).hexdigest()
        cache_key = self._cache_key(content_hash, profile, auto_detect)
        manifest_name = f"{MANIFESTS_PREFIX}/{cache_key}.json"

        cached = self._read_cached_response(manifest_name)
        if cached is not None:
            return {**cached, "duplicate": True}

        if auto_detect:
            layout_analysis = self.document_analyzer.analyze_bytes(
                content, "prebuilt-layout"
            )
            detected_model_id = classify_document(get_lines(layout_analysis))
            profile = get_profile(detected_model_id)
            analysis = (
                layout_analysis
                if profile.model_id == "prebuilt-layout"
                else self.document_analyzer.analyze_bytes(
                    content, profile.model_id
                )
            )
        else:
            analysis = self.document_analyzer.analyze_bytes(
                content, profile.model_id
            )
        assert profile is not None
        result = extract_result(analysis, profile)
        has_ocr_text = any(line.strip() for line in get_lines(analysis))
        if not has_ocr_text and not self._has_extracted_values(result):
            raise UnreadableDocumentError(
                "No readable text or fields were found in the document."
            )

        blob_name, blob_url = self._upload_source(
            content, content_type, content_hash
        )
        full_ocr_blob_name, full_ocr_blob_url = self._upload_full_ocr(
            cache_key, analysis
        )
        result["fullOcrBlobName"] = full_ocr_blob_name
        result["fullOcrBlobUrl"] = full_ocr_blob_url

        # Result is saved locally for debugging and inspection, but not used by the workflow.
        self._save_local_result(cache_key, result)

        self._save_local_result(f"{cache_key}_analysis", analysis)

        ocr_blob_name, ocr_blob_url = self._upload_result(cache_key, result)
        response: dict[str, Any] = {
            "blobName": blob_name,
            "blobUrl": blob_url,
            "ocrBlobName": ocr_blob_name,
            "ocrBlobUrl": ocr_blob_url,
            "fullOcrBlobName": full_ocr_blob_name,
            "fullOcrBlobUrl": full_ocr_blob_url,
            "modelId": profile.model_id,
            "duplicate": False,
        }
        if self.foundry_agent:
            from src.processing.summarize import run_agent

            response["summary"] = run_agent(analysis, profile, self.foundry_agent)

        # The manifest is written last, so failed runs are retried on the next call.
        self.storage.upload(
            manifest_name,
            json.dumps(response, ensure_ascii=False).encode("utf-8"),
            JSON_CONTENT_TYPE,
        )
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print(f"Execution time: {execution_time} seconds")
        return response

    def _cache_key(
        self, content_hash: str, profile: Profile | None, auto_detect: bool
    ) -> str:
        """Key cached results by file bytes and settings that affect output."""
        fingerprint: dict[str, Any] = {
            "schemaVersion": CACHE_SCHEMA_VERSION,
            "autoDetect": auto_detect,
            "foundryAgent": self._foundry_fingerprint(),
        }
        if auto_detect:
            fingerprint["classifierVersion"] = CLASSIFIER_VERSION
            fingerprint["profiles"] = {
                model_id: {
                    "prompt": profile.prompt,
                    "hints": profile.hints,
                    "maxChars": profile.max_chars,
                    "kind": profile.kind,
                    "fields": profile.fields,
                }
                for model_id, profile in PROFILES.items()
            }
        elif profile is not None:
            fingerprint.update(
                {
                    "modelId": profile.model_id,
                    "prompt": profile.prompt,
                    "hints": profile.hints,
                    "maxChars": profile.max_chars,
                    "kind": profile.kind,
                    "fields": profile.fields,
                }
            )
        encoded = json.dumps(
            fingerprint, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        profile_hash = hashlib.sha256(encoded).hexdigest()
        return hashlib.sha256(
            f"{CACHE_SCHEMA_VERSION}:{content_hash}:{profile_hash}".encode("ascii")
        ).hexdigest()

    def _has_extracted_values(self, result: dict[str, Any]) -> bool:
        """Return whether a model produced at least one usable field value."""
        for field in result.get("fields", {}).values():
            for value in (field.get("value"), field.get("content")):
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                if isinstance(value, (list, dict, tuple, set)) and not value:
                    continue
                return True
        return False

    def _foundry_fingerprint(self) -> dict[str, str | None] | None:
        """Refresh cached summaries when the configured agent version changes."""
        if self.foundry_agent is None:
            return None
        return {
            "clientType": type(self.foundry_agent).__qualname__,
            "agentName": getattr(self.foundry_agent, "agent_name", None),
            "agentVersion": getattr(self.foundry_agent, "agent_version", None),
        }

    def _read_cached_response(self, manifest_name: str) -> dict[str, Any] | None:
        """Load a completed duplicate response, if one has been stored."""
        if not self.storage.exists(manifest_name):
            return None
        try:
            cached = json.loads(self.storage.download(manifest_name))
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            return None
        return cached if isinstance(cached, dict) else None

    def _upload_source(
        self,
        content: bytes,
        content_type: str,
        content_hash: str,
    ) -> tuple[str, str]:
        """Upload original bytes under a deterministic content hash."""
        blob_name = f"{UPLOADS_PREFIX}/{content_hash}"
        blob_url = self.storage.upload(blob_name, content, content_type)
        return blob_name, blob_url

    def _upload_result(
        self, cache_key: str, result: dict[str, Any]
    ) -> tuple[str, str]:
        """Upload the compact result JSON and return its name and URL."""
        result_name = f"{RESULTS_PREFIX}/{cache_key}_ocr_result.json"
        content = json.dumps(result, ensure_ascii=False).encode("utf-8")
        result_url = self.storage.upload(result_name, content, JSON_CONTENT_TYPE)
        return result_name, result_url

    def _upload_full_ocr(
        self, cache_key: str, analysis: dict[str, Any]
    ) -> tuple[str, str]:
        """Store the complete Document Intelligence analysis separately."""
        full_ocr_name = f"{FULL_OCR_PREFIX}/{cache_key}_full_ocr_result.json"
        content = json.dumps(analysis, ensure_ascii=False).encode("utf-8")
        full_ocr_url = self.storage.upload(
            full_ocr_name, content, JSON_CONTENT_TYPE
        )
        return full_ocr_name, full_ocr_url

    def _save_local_result(
        self,
        cache_key: str,
        result: dict[str, Any],
    ) -> None:
        """Save the compact extraction result under data/results."""
        result_directory = Path(__file__).resolve().parents[2] / "data" / "results"
        result_directory.mkdir(parents=True, exist_ok=True)
        output_path = result_directory / f"{cache_key}_ocr_result.json"
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
