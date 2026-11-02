from src.processing.extractors import fields_to_text
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
