# Custom Model Schema: Microsoft 10-Q

## Model ID

```text
microsoft-10q-v1
```

## Fields to label

Use these exact field names in Azure Document Intelligence Studio:

| Field name | Type | Label this value |
|---|---|---|
| `companyName` | String | Registered company name, such as `MICROSOFT CORPORATION` |
| `commissionFileNumber` | String | SEC commission file number |
| `reportingPeriodEndDate` | Date or string | End date of the quarterly reporting period |
| `incorporationState` | String | State or jurisdiction of incorporation |
| `companyAddress` | String | Company mailing or registered address |
| `telephoneNumber` | String | Company telephone number |
| `tickerSymbols` | String or array | Trading symbols listed in the filing |
| `exchangeNames` | String or array | Exchange names where the securities are registered |

## Create the model in Document Intelligence Studio

1. Open [Document Intelligence Studio](https://documentintelligence.ai.azure.com/).
2. Select **Custom extraction model**.
3. Connect the Azure Document Intelligence resource used by this project.
4. Create a project named `microsoft-10q`.
5. Upload `sample-layout.pdf`.
6. Add the eight field names listed above.
7. Label each field value in the document.
8. Add additional representative 10-Q documents if available.
9. Train the model.
10. Test the model against a document that was not used for labeling.
11. Publish the model with the ID:

```text
microsoft-10q-v1
```

Custom extraction accuracy improves when training documents contain the same
document type and several layout variations. One document can be used to
prototype the schema, but additional documents are recommended before
production use.

## Project configuration

After the model is trained and published, set this in the project `.env` file:

```env
DOCUMENT_INTELLIGENCE_MODEL_ID=microsoft-10q-v1
```

Set `DOCUMENT_INTELLIGENCE_MODEL_ID=microsoft-10q-v1` to use model-extracted
fields by default, or pass `?modelId=microsoft-10q-v1` to the analysis API.
The model profile provides field values and confidence scores; the existing
`prebuilt-layout` profile uses an OCR-based fallback for 10-Q cover fields.

Keep the existing endpoint and key variables:

```env
DOCUMENT_INTELLIGENCE_ENDPOINT=https://<resource>.cognitiveservices.azure.com/
DOCUMENT_INTELLIGENCE_KEY=<your-key>
DOCUMENT_INTELLIGENCE_MODEL_ID=microsoft-10q-v1
```

## Run the model

```powershell
.\.venv\Scripts\python.exe -m scripts.document_ocr `
  "C:\path\to\sample-layout.pdf" `
  --model-id microsoft-10q-v1
```

The CLI writes its page-oriented OCR result to:

```text
data\results\sample-layout_ocr_result.json
```

## API result shape

```json
{
  "fields": {
    "companyName": {
      "value": "MICROSOFT CORPORATION",
      "content": "MICROSOFT CORPORATION",
      "confidence": 0.95
    },
    "commissionFileNumber": {
      "value": "001-37845",
      "content": "001-37845",
      "confidence": 0.95
    }
  },
  "fullOcrBlobName": "full-ocr/<cache-key>_full_ocr_result.json",
  "fullOcrBlobUrl": "https://<account>.blob.core.windows.net/<container>/full-ocr/<cache-key>_full_ocr_result.json"
}
```

Fields that are not found in a document may be omitted or returned with a
null value. Always inspect the confidence score before using a value in a
business workflow.
