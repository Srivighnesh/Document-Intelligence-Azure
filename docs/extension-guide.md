# Multi-Model and Classifier Extension Plan

This plan describes how to support multiple Azure Document Intelligence
models and automatically select the correct model for each document.

## Target model catalog

Keep the supported models in one catalog instead of scattering model IDs
throughout the application.

| Document type | Model ID | Processing purpose |
|---|---|---|
| General OCR | `prebuilt-read` | Text, pages, lines, words |
| General layout | `prebuilt-layout` | Text, tables, selection marks |
| Invoice | `prebuilt-invoice` | Vendor, totals, dates, line items |
| Receipt | `prebuilt-receipt` | Merchant, totals, tax, items |
| Identity document | `prebuilt-idDocument` | Identity and expiry fields |
| Tax or annual filing | `10q-model-v1` | Published custom extraction model |
| Contract | `contract-model-v1` | Published custom extraction model |
| Custom form | `custom-form-v1` | Published custom extraction model |

Replace example custom IDs with the IDs published in the Document Intelligence
resource.

## Planned architecture

```text
Uploaded document
        |
        v
DocumentClassifier
        |
        +--> invoice       -> prebuilt-invoice
        +--> receipt       -> prebuilt-receipt
        +--> identity      -> prebuilt-idDocument
        +--> annual filing -> 10q-model-v1
        +--> contract      -> contract-model-v1
        +--> unknown       -> prebuilt-layout
        |
        v
DocumentAnalyzer
        |
        v
Model-specific result parser
        |
        v
Structured JSON
        |
        v
Optional Foundry post-processing
```

## Phase 1: Create a model catalog

Add a typed catalog module, for example:

```text
src/models/model_catalog.py
```

Each entry should contain:

```python
{
    "document_type": "invoice",
    "model_id": "prebuilt-invoice",
    "parser": "invoice",
}
```

The catalog should be the only place that maps a document type to a model ID.
The existing `DocumentAnalyzer` should continue accepting a model ID and
should not contain document-type branching.

## Phase 2: Add classifier strategies

Create a classifier service, for example:

```text
src/services/document_classifier.py
```

The classifier should return a catalog entry or model ID.

### Strategy A: Filename and content type

Use only as a simple first version:

```text
invoice.pdf   -> invoice
receipt.jpg   -> receipt
```

This is fast but unreliable when filenames are generic.

### Strategy B: OCR keyword classification

Run `prebuilt-layout` first, then inspect compact OCR text:

```text
"invoice number", "amount due"     -> invoice
"receipt", "subtotal", "change"    -> receipt
"commission file number", "10-Q"   -> annual filing
"agreement", "terms and conditions" -> contract
```

Add confidence thresholds and an `unknown` result. Never select a specialized
model when the classifier confidence is too low.

### Strategy C: Foundry classification

Use the existing Foundry agent only when natural-language classification is
needed. Send compact OCR text and require a strict response:

```json
{
  "documentType": "invoice",
  "confidence": 0.96
}
```

Validate the response before selecting a model. Foundry should classify or
interpret the document; Document Intelligence should perform the extraction.

## Phase 3: Update the workflow

Extend `DocumentWorkflow` with an optional classification path:

```text
if model_id is provided:
    use the requested model
else:
    classify the document
    select the catalog model

analyze bytes with DocumentAnalyzer
parse using the selected model parser
write structured output
```

Keep explicit `--model-id` and configured model IDs higher priority than
automatic classification. This allows deterministic testing and manual
overrides.

## Phase 4: Add model-specific parsers

Create separate parsers under:

```text
src/models/parsers/
```

Recommended modules:

```text
ocr_parser.py
layout_parser.py
invoice_parser.py
receipt_parser.py
identity_parser.py
custom_form_parser.py
```

OCR and layout results contain `content`, `pages`, `lines`, and `words`.
Prebuilt and custom extraction models may contain
`documents[].fields`. Do not force every model through the current OCR-only
writer.

Each parser should:

1. Accept the raw Azure analysis dictionary.
2. Handle missing fields with `None`.
3. Preserve confidence values.
4. Return a typed Pydantic model.
5. Avoid Azure authentication or network calls.

## Phase 5: API behavior

Support two request modes:

```text
POST /documents/analyze
```

Uses the configured default model.

```text
POST /documents/analyze?model_id=prebuilt-invoice
```

Uses an explicit model override.

Future classifier mode can be enabled with:

```text
POST /documents/analyze?classify=true
```

The response should include:

```json
{
  "documentType": "invoice",
  "modelId": "prebuilt-invoice",
  "classificationConfidence": 0.96,
  "extractedFields": {},
  "summary": {}
}
```

Do not expose API keys, Key Vault values, or internal authentication details
in API errors.

## Configuration

Keep model IDs and classifier settings in non-secret configuration:

```env
DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-layout
DOCUMENT_CLASSIFIER_ENABLED=false
DOCUMENT_CLASSIFIER_MIN_CONFIDENCE=0.80
```

Document Intelligence endpoints, the Document Intelligence key, Foundry
endpoint, and Blob account URL remain in Azure Key Vault. Use
`DefaultAzureCredential` through `src/config.py`.

## Testing plan

Test each model independently before enabling classification:

```powershell
.\.venv\Scripts\python.exe -m scripts.document_ocr `
  "C:\documents\invoice.pdf" `
  --model-id prebuilt-invoice
```

Add unit tests for:

- Every catalog entry.
- Filename/content-type classification.
- OCR keyword classification.
- Low-confidence fallback to `prebuilt-layout`.
- Explicit model override.
- Unknown document type.
- Missing model-specific fields.
- Invalid Foundry classifier JSON.

Use representative fixtures for invoices, receipts, identity documents,
annual filings, contracts, and unknown documents. Do not use real secrets in
fixtures or tests.

## Rollout order

1. Add the model catalog.
2. Add model-specific Pydantic parsers.
3. Add explicit model selection to the workflow.
4. Add deterministic keyword classification.
5. Add confidence thresholds and unknown fallback.
6. Add optional Foundry classification.
7. Enable automatic classification only after fixture tests pass.

This order keeps the existing OCR workflow working while allowing new models
to be introduced incrementally.
