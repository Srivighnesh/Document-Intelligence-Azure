# Document Intelligence Architecture

## Purpose

Extract text or document-specific fields from local documents or URLs with an
Azure Document Intelligence model, validate the result with Pydantic, and
write a source-specific JSON file.

## Runtime flow

```text
CLI arguments and .env
          |
          v
scripts/document_ocr.py
          |
          v
DocumentAnalyzer
  - builds URL or byte request
  - calls the selected custom model
          |
          v
Azure analysis dictionary
          |
          v
ResultWriter
  - maps Azure fields to Pydantic models
  - writes source-specific JSON
          |
          v
data/results/<document>_ocr_result.json
```

## Components

| Component | Responsibility |
|---|---|
| `scripts/document_ocr.py` | OCR CLI orchestration |
| `src/services/document_intelligence.py` | Azure client and document submission |
| `src/services/foundry_agent.py` | Foundry agent integration |
| `src/models/result_writer.py` | Pydantic validation and compact JSON serialization |
| `data/results/` | Generated analysis results |

## Design principles

- Keep Azure SDK concerns inside `DocumentAnalyzer`.
- Keep output formatting and validation inside `ResultWriter`.
- Keep the CLI thin so other entry points can reuse the components.
- Use the custom model ID as configuration, not as source-code logic.
- Add future analyzers as separate classes instead of modifying existing ones.

## Configuration

Create a `.env` file in the project root:

```env
DOCUMENT_INTELLIGENCE_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
DOCUMENT_INTELLIGENCE_KEY=<key>
DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-read
```

Never commit `.env` or Azure keys.
