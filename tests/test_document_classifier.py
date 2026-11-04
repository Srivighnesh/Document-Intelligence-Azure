from src.processing.document_classifier import classify_document


def test_routes_e_aadhaar_letter_to_identity_model() -> None:
    lines = [
        "Government of India",
        "Unique Identification Authority of India",
        "Enrolment No.",
        "Your Aadhaar No.",
        "VID",
    ]

    assert classify_document(lines) == "prebuilt-idDocument"


def test_routes_aadhaar_card_with_dob_to_identity_model() -> None:
    lines = [
        "Government of India",
        "DOB: 08/01/2002",
        "Aadhaar",
        "9522 4107 1384",
    ]

    assert classify_document(lines) == "prebuilt-idDocument"


def test_routes_other_indian_identity_documents() -> None:
    assert classify_document(["Permanent Account Number", "Income Tax Department"]) == (
        "prebuilt-idDocument"
    )
    assert classify_document(["Elector Photo Identity Card", "Voter ID"]) == (
        "prebuilt-idDocument"
    )


def test_invoice_signals_win_over_generic_identity_number_cue() -> None:
    lines = ["Invoice Number: 1234", "Document Number: 789"]

    assert classify_document(lines) == "prebuilt-invoice"
