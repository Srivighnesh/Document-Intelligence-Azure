# Document Intelligence and Foundry Architecture

## Purpose

The service accepts a Base64 JSON request, stores the decoded upload in Azure
Blob Storage, analyzes its bytes with Azure AI Document Intelligence, and
stores a compact extraction result. Microsoft Foundry summaries are optional
and disabled by default.

The API currently processes requests synchronously. A model profile can be
selected from the profiles configured in `src/processing/profiles.py`; the
default is `prebuilt-layout`. There is no automatic document classification,
background queue, or MCP endpoint.

## Runtime architecture

```mermaid
flowchart LR
    U[Client] -->|Base64 JSON + optional modelId| API[FastAPI]
    CFG[Configuration] -->|DefaultAzureCredential| KV[Azure Key Vault]
    API -->|validate and decode| WF[DocumentWorkflow]
    WF -->|original bytes under uploads/| BLOB[Azure Blob Storage]
    WF -->|bytes + selected model ID| DI[Azure Document Intelligence]
    DI -->|analysis| WF
    WF -->|profile fields or OCR fallback| EX[Profile extractors]
    EX -->|fields-only JSON under results/| BLOB2[Azure Blob Storage]
    EX -->|local copy| LOCAL[data/results/]
    WF -. optional .->|analysis + profile| FA[FoundryClient]
    FA -->|optional summary| WF
    WF -->|Blob metadata + modelId + optional summary| API
    API --> U
```

Azure SDK clients use `DefaultAzureCredential`. The configuration module reads
non-secret settings from environment variables or `.env` and loads configured
service endpoints and credentials from Key Vault.

## Request sequence

`POST /documents/analyze` performs these steps:

1. Validate the filename and supported media type, then `Base64Document`
   validates and decodes the Base64 content with a 10 MB decoded limit.
2. Resolve the requested model profile, or use the configured default.
3. Upload the original file under `uploads/` in the configured Blob container.
4. Submit the document bytes to Document Intelligence using the profile's
   model ID.
5. Extract allowlisted fields according to the profile, using OCR fallback
   parsing when model fields are absent.
6. Save only the compact `fields` JSON under `results/<document>_ocr_result.json`.
7. If enabled, send profile-selected text to the Foundry agent.
8. Return original and result Blob metadata, the model ID, and an optional summary.

The request JSON contains `filename`, `contentType`, `contentBase64`, and
optional `modelId`. The response contains `blobName`, `blobUrl`,
`ocrBlobName`, `ocrBlobUrl`, and `modelId`; it includes `summary` only when
Foundry is enabled. The service returns Blob URLs but does not create SAS URLs.
The client waits for storage, OCR, and any enabled Foundry call to finish.

## Components

| Path | Responsibility |
|---|---|
| `Backend/api.py` | FastAPI health and analysis routes, upload validation, workflow construction |
| `src/config.py` | Environment settings and Key Vault secret loading |
| `src/processing/base64_document.py` | Validates, decodes, and encodes Base64 content |
| `src/services/document_workflow.py` | Coordinates upload, OCR storage, profile selection, and Foundry processing |
| `src/services/blob_storage.py` | Uploads and downloads documents in Blob Storage |
| `src/services/document_intelligence.py` | Calls the configured Document Intelligence model |
| `src/services/foundry/client.py` | Invokes the configured Foundry agent |
| `src/services/foundry/response.py` | Parses JSON responses and preserves plain text responses |
| `src/processing/profiles.py` | Maps model IDs to prompts, extractor kinds, hints, and field allowlists |
| `src/processing/text_select.py` | Selects and compacts OCR lines |
| `src/processing/extractors.py` | Extracts OCR text or allowlisted model fields |
| `src/processing/summarize.py` | Applies the profile and runs the Foundry client |
| `src/models/result_writer.py` | Shapes and writes CLI OCR result JSON |
| `scripts/document_ocr.py` | Runs OCR on a local file or URL from the command line |
| `scripts/foundry_ocr.py` | Sends an existing OCR JSON result to Foundry |
| `data/results/` | Local compact CLI and API results plus Foundry JSON files (ignored by Git) |

## Configuration and identity

Keep non-secret values in `.env` and credentials in Key Vault. The current
configuration includes the Key Vault URL, storage container, default model ID,
and optional `FOUNDRY_ENABLED` setting. Foundry endpoint and agent settings are
loaded only when enabled. Key Vault supplies the Document Intelligence
endpoint and key, optional Foundry project endpoint, and Blob Storage account URL.

Azure SDK clients authenticate through `DefaultAzureCredential`. Local
development can use Azure CLI sign-in; deployed services should use a managed
identity where possible. The identity needs Key Vault secret access, Blob data
access, and permission to use the configured Foundry agent. Azure management
plane `Contributor` alone does not grant Blob data access.

## Design principles

- Keep Azure SDK calls within their service wrappers.
- Keep request validation and HTTP error mapping in the API layer.
- Keep orchestration in `DocumentWorkflow` so the API and CLI can reuse
  processing components.
- Keep model-specific prompts, hints, extraction kinds, and field allowlists
  in profiles rather than branching throughout the workflow.
- Store the compact result JSON under the `results/` Blob prefix.
- Do not log document contents or secrets.

## Current limitations and extension points

- The API handles each upload synchronously; high-volume deployments may need
  a job queue, workers, and a status/result endpoint.
- Model choice is explicit or configured by default. Classification and
  confidence-based routing are future work.
- Blob uploads use unique names under `uploads/`; retries create a new blob.
  Add idempotency keys if retries should reuse an earlier result.
- Compact CLI and API results are written to `data/results/`; multi-instance
  deployments should use durable shared storage.
- Add a model by adding a profile in `src/processing/profiles.py`; see the
  [model extension guide](model-extension-guide.md).
- An MCP endpoint is not part of the current runtime. Add one only if a
  Foundry agent needs to call this service as a tool.

See the [README](../README.md) for setup and usage instructions and the
[Azure CLI setup guide](azure-cli-setup.md) for local authentication.
