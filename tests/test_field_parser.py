from src.processing.field_parser import ProfileFieldParser, TenQFieldParser
from src.processing.profiles import Profile, get_profile


def test_parse_10q_cover_page_fields() -> None:
    lines = [
        "For the Quarterly Period Ended March 31, 2020",
        "Commission File Number 001-37845",
        "MICROSOFT CORPORATION",
        "WASHINGTON",
        "(STATE OF INCORPORATION)",
        "ONE MICROSOFT WAY, REDMOND, WASHINGTON 98052-6399",
        "(425) 882-8080",
        "Trading Symbol",
        "Name of exchange on which registered",
        "Common stock, $0.00000625 par value per share",
        "MSFT",
    ]

    fields = TenQFieldParser().parse(lines, get_profile("prebuilt-layout"))

    expected = {
        "companyName": "MICROSOFT CORPORATION",
        "commissionFileNumber": "001-37845",
        "reportingPeriodEndDate": "March 31, 2020",
        "incorporationState": "WASHINGTON",
        "companyAddress": "ONE MICROSOFT WAY, REDMOND, WASHINGTON 98052-6399",
        "telephoneNumber": "(425) 882-8080",
        "tickerSymbols": ["MSFT"],
        "exchangeNames": None,
    }
    for name, value in expected.items():
        assert fields[name] == {
            "value": value,
            "content": "MSFT" if name == "tickerSymbols" else value,
            "confidence": None,
        }


def test_parse_invoice_profile_fields() -> None:
    fields = ProfileFieldParser().parse(
        ["Vendor: ACME Supplies", "Invoice Number: INV-42", "Invoice Date: 2026-10-01"],
        get_profile("prebuilt-invoice"),
    )

    assert fields["VendorName"]["value"] == "ACME Supplies"
    assert fields["InvoiceId"]["value"] == "INV-42"
    assert fields["InvoiceDate"]["value"] == "2026-10-01"
    assert fields["AmountDue"]["value"] is None


def test_parse_receipt_and_identity_profile_fields() -> None:
    parser = ProfileFieldParser()
    receipt = parser.parse(
        ["Merchant Name: Cafe", "Transaction Date: 2026-10-01", "Total: $12.50"],
        get_profile("prebuilt-receipt"),
    )
    identity = parser.parse(
        ["First Name: Ada", "Last Name: Lovelace", "Date of Birth: 1815-12-10"],
        get_profile("prebuilt-idDocument"),
    )

    assert receipt["MerchantName"]["value"] == "Cafe"
    assert receipt["Total"]["value"] == "$12.50"
    assert identity["FirstName"]["value"] == "Ada"
    assert identity["LastName"]["value"] == "Lovelace"
    assert identity["DateOfBirth"]["value"] == "1815-12-10"


def test_10q_parser_returns_only_fields_configured_by_profile() -> None:
    profile = Profile("prebuilt-layout", "{data}", kind="fields", fields=("companyName",))

    fields = TenQFieldParser().parse(
        ["Commission File Number 001-37845", "MICROSOFT CORPORATION"],
        profile,
    )

    assert fields == {
        "companyName": {
            "value": "MICROSOFT CORPORATION",
            "content": "MICROSOFT CORPORATION",
            "confidence": None,
        }
    }
