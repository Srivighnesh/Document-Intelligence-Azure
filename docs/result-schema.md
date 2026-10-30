# Result Schema

The writer intentionally stores only fields returned by the custom model. OCR
layout data, polygons, lines, and tables are not copied into the compact
custom-model result.

## Pydantic models

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

## Field mapping

Azure custom-model fields use typed keys such as `valueString`,
`valueNumber`, `valueDate`, or `valueBoolean`. `ResultWriter._field_value`
normalizes the first typed `value*` property to the stable output property
`value`.
