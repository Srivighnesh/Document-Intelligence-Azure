# Adding Document-Specific Models

This project supports changing the Azure Document Intelligence model and its
Foundry post-processing without adding model-specific workflow logic.

## Model choices

| Document type | Model ID | Typical output |
|---|---|---|
| General OCR | `prebuilt-read` | Text, pages, lines, words, confidence |
| General layout | `prebuilt-layout` | OCR plus tables and selection marks |
| Invoices | `prebuilt-invoice` | Vendor, invoice ID, dates, totals, tax, line items |
| Receipts | `prebuilt-receipt` | Merchant, date, totals, tax, purchased items |
| Identity documents | `prebuilt-idDocument` | Name, date of birth, expiry, card number, address |
| Custom document type | `<published-model-id>` | Fields defined by your custom model |

## Run a different model

Override the model for one run:

```powershell
.\.venv\Scripts\python.exe -m scripts.document_ocr `
  "C:\documents\invoice.pdf" `
  --model-id "prebuilt-invoice"
```

Or set the default model in `.env`:

```env
DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-invoice
```

For an API request, pass the model in the JSON body or as `?modelId=`. Use
`modelId=auto` to classify from OCR text cues before selecting one of the
supported profiles. Auto mode currently recognizes invoice, receipt, identity,
and 10-Q cues; unclear documents fall back to `prebuilt-layout`. This is a
keyword-based router, not a trained classifier.

The generated file remains source-specific:

```text
data/results/invoice_ocr_result.json
```

## Invoice flow

```text
invoice.pdf
    |
    v
prebuilt-invoice
    |
    v
invoice_ocr_result.json
    |
    +--> application reads invoice fields
    |
    +--> optional Foundry summary
```

## Important output difference

`prebuilt-read` and `prebuilt-layout` return OCR-oriented data such as
`content`, `pages`, `lines`, and `words`.

`prebuilt-invoice`, `prebuilt-receipt`, and custom extraction models return
structured fields under `documents[].fields`.

The API profiles select allowlisted fields from structured models and use
profile-specific OCR fallback parsing when model fields are absent. The CLI
`ResultWriter` continues to write its separate page-oriented OCR schema.

The API cache key uses file contents and profile settings rather than the
filename. A same-content, same-profile retry reuses its manifest. A different
model profile produces a separate extraction result. The standalone OCR CLI
does not use this API cache or auto routing.

## Recommended invoice model

For invoices, use:

```env
DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-invoice
```

Common fields include:

```text
VendorName
CustomerName
InvoiceId
InvoiceDate
DueDate
InvoiceTotal
SubTotal
TotalTax
AmountDue
Items
```

Field availability depends on the document and model response. Always check
for missing fields and inspect confidence values before using them in a
business process. Azure's prebuilt ID model only returns its `Address` model
field for supported driver license types; for other IDs, the project tries an
OCR-label fallback if an address label is present.

## Adding a custom model

1. Train and publish a model in Document Intelligence Studio.
2. Copy the published model ID.
3. Add one `Profile` entry to `src/processing/profiles.py` with the model ID,
   prompt, `kind="ocr"` for page-line text or `kind="fields"` for structured
   fields, any optional text hints or field allowlist, and maximum prompt size.
4. Set the ID in `.env` or pass it with `--model-id`.
5. Add a dedicated Pydantic output model only if the fields are fixed.

The workflow uses `get_profile()` and `run_agent()` for every model. Adding a
model means adding one `Profile` in `src/processing/profiles.py`; no new
caller or Foundry logic is required.

Example:

```powershell
.\.venv\Scripts\python.exe -m scripts.document_ocr `
  "C:\documents\custom-form.pdf" `
  --model-id "custom-form-v1"
```

## Processing structure

| Module | Responsibility |
|---|---|
| `src/processing/profiles.py` | Model IDs, prompts, extractor kinds, hints, fields, and limits |
| `src/processing/text_select.py` | Pure OCR line selection and compaction |
| `src/processing/extractors.py` | OCR or structured-field prompt text extraction |
| `src/processing/summarize.py` | Applies a profile and invokes Foundry |
| `src/services/foundry/client.py` | Azure Foundry SDK access |
| `src/services/foundry/response.py` | JSON/text response parsing |

## Foundry remains optional

Use Foundry only when you need summarization, natural-language questions,
classification, or additional reasoning. The Document Intelligence model
should perform document extraction; Foundry should not duplicate extraction
unless there is a specific downstream requirement.
