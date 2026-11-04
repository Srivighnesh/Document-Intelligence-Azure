# Result Schemas

The project has separate API and standalone CLI result formats. The API writes
a compact, profile-based result and a separate full Document Intelligence
analysis JSON. The standalone CLI writes its page-oriented OCR result locally.

## CLI Pydantic models

### `ExtractedField`

| Property | Type | Description |
|---|---|---|
| `value` | `Any \| None` | Typed value returned by Azure, such as text, number, date, boolean, list, or object |
| `content` | `str \| None` | Original text detected for the field |
| `confidence` | `float \| None` | Azure confidence score |

### `ExtractedDocument`

| Property | Type | Description |
|---|---|---|
| `fields` | `dict[str, ExtractedField]` | Dynamic fields defined by the custom extraction model |

### `ExtractionResult`

| Property | Type | JSON name |
|---|---|---|
| `model_id` | `str` | `modelId` |
| `source` | `str` | `source` |
| `documents` | `list[ExtractedDocument]` | `documents` |

## Example JSON

```json
{
  "modelId": "invoice-model-v1",
  "source": "invoice.pdf",
  "documents": [
    {
      "fields": {
        "invoiceNumber": {
          "value": "INV-1001",
          "content": "INV-1001",
          "confidence": 0.98
        },
        "totalAmount": {
          "value": 1250.5,
          "content": "$1,250.50",
          "confidence": 0.96
        }
      }
    }
  ]
}
```

## API result shape

The compact API result stores configured profile fields under `fields`. Missing
allowlisted fields have null `value`, `content`, and `confidence` properties.
Nested Azure spatial metadata is removed from field values. It also contains
Blob name and URL properties linking to the full analysis JSON.

```json
{
  "fields": {
    "InvoiceId": {
      "value": "INV-1001",
      "content": "INV-1001",
      "confidence": 0.98
    }
  },
  "fullOcrBlobName": "full-ocr/<cache-key>_full_ocr_result.json",
  "fullOcrBlobUrl": "https://<account>.blob.core.windows.net/<container>/full-ocr/<cache-key>_full_ocr_result.json"
}
```

For `prebuilt-idDocument`, the allowlist includes `Address`. The model may
provide it for supported document types; when the model omits it, the API tries
to parse a labeled address from OCR lines. Address fallback depends on the OCR
text including an address label.

The full analysis JSON is uploaded under `full-ocr/` and preserves the complete
Azure response, including OCR pages, lines, tables, model fields, and layout
metadata. It can contain sensitive personal data.

The API response separately returns `blobName`/`blobUrl` for the original,
`ocrBlobName`/`ocrBlobUrl` for the compact result,
`fullOcrBlobName`/`fullOcrBlobUrl` for the full analysis, the selected `modelId`,
and `duplicate`. `duplicate` is false for a new completed run and true when a
cached manifest is reused.

## Field mapping

Azure custom-model fields use typed keys such as `valueString`,
`valueNumber`, `valueDate`, or `valueBoolean`. The API result extractor uses
`src.processing.field_values.first_typed_value` to normalize the first typed
value property. API results are shaped by `src.processing.extractors` using
the selected profile's field allowlist.
