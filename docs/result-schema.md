# Result Schemas

The project has separate local CLI and API result formats. API results contain
only allowlisted profile fields; CLI results retain page-oriented OCR output.

The API result contains allowlisted model fields and removes Azure layout
metadata. The CLI writer separately stores page-oriented OCR data for local
analysis workflows.

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

The API stores the configured profile fields under a `fields` object. Missing
allowlisted fields have null `value`, `content`, and `confidence` properties.
Nested Azure spatial metadata is removed from values.

```json
{
  "fields": {
    "InvoiceId": {
      "value": "INV-1001",
      "content": "INV-1001",
      "confidence": 0.98
    }
  }
}
```

## Field mapping

Azure custom-model fields use typed keys such as `valueString`,
`valueNumber`, `valueDate`, or `valueBoolean`. The API result extractor uses
`src.processing.field_values.first_typed_value` to normalize the first typed
value property. API results are shaped by `src.processing.extractors` using
the selected profile's field allowlist.
