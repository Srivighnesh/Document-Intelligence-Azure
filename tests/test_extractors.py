from src.processing.extractors import extract_result, fields_to_text
from src.processing.profiles import Profile


def test_fields_to_text_applies_allowlist() -> None:
    analysis = {
        "documents": [
            {
                "fields": {
                    "InvoiceId": {"content": "INV-1"},
                    "Ignored": {"content": "secret"},
                }
            }
        ]
    }
    profile = Profile("invoice", "{data}", kind="fields", fields=("InvoiceId",))

    assert fields_to_text(analysis, profile) == "InvoiceId: INV-1"


def test_fields_to_text_prefers_content_then_value_fallback() -> None:
    analysis = {
        "documents": [
            {
                "fields": {
                    "Content": {"content": "readable", "valueString": "other"},
                    "Value": {"valueNumber": 42},
                }
            }
        ]
    }
    profile = Profile("fields", "{data}", kind="fields")

    assert fields_to_text(analysis, profile) == (
        "Content: readable\nValue: 42"
    )


def test_fields_to_text_marks_low_confidence() -> None:
    analysis = {
        "documents": [
            {"fields": {"Name": {"content": "Ada", "confidence": 0.5}}}
        ]
    }
    profile = Profile("fields", "{data}", kind="fields")

    assert fields_to_text(analysis, profile) == "Name: Ada (low confidence)"


def test_empty_fields_fall_back_to_ocr_text() -> None:
    analysis = {
        "documents": [{"fields": {}}],
        "pages": [{"lines": [{"content": "OCR text"}]}],
    }
    profile = Profile("fields", "{data}", kind="fields")

    assert fields_to_text(analysis, profile) == "OCR text"


def test_extract_result_returns_allowlisted_fields() -> None:
    analysis = {"documents": [{"fields": {
        "InvoiceId": {"valueString": "INV-1", "content": "INV-1", "confidence": 0.95},
        "Ignored": {"valueString": "secret"},
    }}]}
    profile = Profile("invoice", "{data}", kind="fields", fields=("InvoiceId",))

    result = extract_result(analysis, profile)

    assert result == {
        "fields": {
            "InvoiceId": {"value": "INV-1", "content": "INV-1", "confidence": 0.95}
        }
    }


def test_extract_result_falls_back_to_ocr_content() -> None:
    analysis = {"documents": [{"fields": {}}], "pages": [{"lines": [{"content": "OCR text"}]}]}
    profile = Profile("prebuilt-layout", "{data}", kind="fields", fields=("companyName", "exchangeNames"))

    assert extract_result(analysis, profile) == {
        "fields": {
            "companyName": {"value": None, "content": None, "confidence": None},
            "exchangeNames": {"value": None, "content": None, "confidence": None},
        }
    }


def test_model_fields_take_precedence_over_10q_parser() -> None:
    analysis = {
        "documents": [{"fields": {
            "companyName": {"valueString": "MODEL COMPANY", "content": "MODEL COMPANY", "confidence": 0.99}
        }}],
        "pages": [{"lines": [{"content": "Commission File Number 001-37845"}]}],
    }
    profile = Profile("prebuilt-layout", "{data}", kind="fields", fields=("companyName", "commissionFileNumber"))

    result = extract_result(analysis, profile)

    assert result["fields"]["companyName"]["value"] == "MODEL COMPANY"
    assert result["fields"]["commissionFileNumber"] == {
        "value": None, "content": None, "confidence": None
    }


def test_extract_result_removes_nested_azure_metadata() -> None:
    analysis = {"documents": [{"fields": {
        "Items": {
            "valueArray": [{
                "type": "object",
                "valueObject": {
                    "Description": {
                        "type": "string",
                        "valueString": "Consulting Services",
                        "content": "Consulting Services",
                        "confidence": 0.9,
                        "boundingRegions": [{"pageNumber": 1}],
                        "spans": [{"offset": 10}],
                    }
                },
                "content": "Consulting Services",
                "confidence": 0.9,
                "boundingRegions": [{"pageNumber": 1}],
            }],
            "content": None,
            "confidence": 0.9,
        }
    }}]}
    profile = Profile("invoice", "{data}", kind="fields", fields=("Items",))

    result = extract_result(analysis, profile)

    assert result == {
        "fields": {
            "Items": {
                "value": [{"Description": "Consulting Services"}],
                "content": None,
                "confidence": 0.9,
            }
        }
    }
