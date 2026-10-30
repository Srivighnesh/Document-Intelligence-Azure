# Adding Document-Specific Models

This project supports changing the Azure Document Intelligence model without
changing the Python code. Use the model ID that matches the document type.

## Model choices

| Document type | Model ID | Typical output |
|---|---|---|
| General OCR | `prebuilt-read` | Text, pages, lines, words, confidence |
| General layout | `prebuilt-layout` | OCR plus tables and selection marks |
| Invoices | `prebuilt-invoice` | Vendor, invoice ID, dates, totals, tax, line items |
| Receipts | `prebuilt-receipt` | Merchant, date, totals, tax, purchased items |
| Identity documents | `prebuilt-idDocument` | Name, date of birth, document number, expiry |
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

Therefore, a production application should use a model-specific Pydantic
writer when it needs typed fields. The current OCR writer is intended for
`prebuilt-read` output.

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
business process.

## Adding a custom model

1. Train and publish a model in Document Intelligence Studio.
2. Copy the published model ID.
3. Set the ID in `.env` or pass it with `--model-id`.
4. Add a dedicated Pydantic output model if the fields are fixed.
5. Keep the Azure request code in `src/services/`.
6. Keep document-specific mapping in a separate analyzer or writer.

Example:

```powershell
.\.venv\Scripts\python.exe -m scripts.document_ocr `
  "C:\documents\custom-form.pdf" `
  --model-id "custom-form-v1"
```

## Foundry remains optional

Use Foundry only when you need summarization, natural-language questions,
classification, or additional reasoning. The Document Intelligence model
should perform document extraction; Foundry should not duplicate extraction
unless there is a specific downstream requirement.
