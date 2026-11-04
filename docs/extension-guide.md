# Auto Routing and Model Extension Guide

This guide describes the current OCR-text router and how to extend its model
profiles and document cues.

## Current model routes

| Content cues | Selected model | Notes |
|---|---|---|
| Invoice number, invoice date, bill to, amount due | `prebuilt-invoice` | The router examines OCR text, not filename. |
| Receipt, merchant, transaction date, cash tendered | `prebuilt-receipt` | Cues are keywords and may overlap with invoices. |
| Aadhaar/Aadhar, UIDAI, PAN, voter ID, passport, license, national ID | `prebuilt-idDocument` | ID field availability varies by document type. |
| Form 10-Q, commission file number, quarterly period ended | `prebuilt-layout` | The current layout profile parses 10-Q cover fields. |
| No strong cue or tied scores | `prebuilt-layout` | This is the fallback route. |

The route definitions and weights are in
`src/processing/document_classifier.py`. Auto mode requires OCR text from
`prebuilt-layout`; it then calls the selected specialized model, except when
layout itself is selected. This can make auto mode use two Document Intelligence
calls for a recognized invoice, receipt, or ID.

Call the API with `modelId=auto` in the body or as a query parameter. An
explicit supported model ID skips classification and uses that model directly.
The API returns the model actually used in its `modelId` field.

## How routing works

1. `DocumentWorkflow` runs `prebuilt-layout` and reads its OCR lines.
2. `classify_document()` scores known phrases for each supported route.
3. The highest score is selected when it is at least 2 and is not tied with
   another route.
4. Low, missing, or tied scores fall back to `prebuilt-layout`.
5. The chosen profile extracts allowlisted fields and can use OCR-label
   fallbacks for missing values.

The classifier is rule-based, not a trained document classifier. It does not
look at the filename. A document with poor OCR or unfamiliar terminology may
fall back to layout. For an unknown document, the current layout profile may
return null 10-Q fields rather than generic key/value extraction.

## Add a document type or improve routing

1. Add the Azure model profile in `src/processing/profiles.py` with its exact
   model ID, fields, prompt, and any OCR hints.
2. Add weighted text cues for the model in
   `src/processing/document_classifier.py` if auto mode should select it.
3. Add regression cases in `tests/test_document_classifier.py` and
   `tests/test_workflow.py`. Include positive cues, ambiguous text, and a
   filename that does not match the document content.
4. Bump `CLASSIFIER_VERSION` when changing auto-routing rules. Auto-mode cache
   keys include this version so old cached routes are not reused.

The ID profile includes `Address`. Azure's ID model may provide the address for
supported driver-license types; for other IDs, the field parser tries a
labeled OCR address fallback. That fallback depends on OCR recognizing an
address label.

## Next step for broad production routing

The current keyword router is useful for a known set of formats but does not
guarantee correct classification for arbitrary documents. For a wide or
changing document catalog, train and publish a Document Intelligence custom
classifier, route its class result to the corresponding profile, and retain an
unknown/review path for low-confidence classifications.

See the [model extension guide](model-extension-guide.md) for profile details
and the [README](../README.md) for API and CLI commands.
