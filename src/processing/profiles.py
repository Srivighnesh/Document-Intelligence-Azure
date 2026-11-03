"""Document Intelligence processing profiles."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Profile:
    """Configure prompt and OCR selection for one model."""

    model_id: str
    prompt: str
    hints: tuple[str, ...] = ()
    max_chars: int = 1500
    kind: Literal["ocr", "fields"] = "ocr"
    fields: tuple[str, ...] = ()


# To support a new model, add one Profile here.
_PROFILE_LIST = [
    Profile(
        model_id="microsoft-10q-v1",
        prompt="Summarize these company and reporting fields concisely:\n{data}",
        hints=(
            "commission file number",
            "period ended",
            "incorporation",
            "telephone",
            "trading symbol",
            "name of exchange",
            "street",
            "address",
        ),
        kind="fields",
        fields=(
            "companyName",
            "commissionFileNumber",
            "reportingPeriodEndDate",
            "incorporationState",
            "companyAddress",
            "telephoneNumber",
            "tickerSymbols",
            "exchangeNames",
        ),
    ),
    Profile(
        model_id="prebuilt-layout",
        prompt=(
            "Summarize these company and reporting fields concisely:\n{data}"
        ),
        hints=(
            "commission file number",
            "period ended",
            "incorporation",
            "telephone",
            "trading symbol",
            "name of exchange",
            "street",
            "address",
        ),
        kind="fields",
        fields=(
            "companyName",
            "commissionFileNumber",
            "reportingPeriodEndDate",
            "incorporationState",
            "companyAddress",
            "telephoneNumber",
            "tickerSymbols",
            "exchangeNames",
        ),
    ),
    Profile(
        model_id="prebuilt-invoice",
        prompt="Summarize these invoice fields concisely:\n{data}",
        kind="fields",
        fields=(
            "VendorName",
            "CustomerName",
            "InvoiceId",
            "InvoiceDate",
            "DueDate",
            "InvoiceTotal",
            "SubTotal",
            "TotalTax",
            "AmountDue",
            "Items",
        ),
    ),
    Profile(
        model_id="prebuilt-receipt",
        prompt="Summarize these receipt fields concisely:\n{data}",
        kind="fields",
        fields=(
            "MerchantName",
            "TransactionDate",
            "Total",
            "Subtotal",
            "TotalTax",
            "Items",
        ),
    ),
    Profile(
        model_id="prebuilt-idDocument",
        prompt="Summarize these identity document fields concisely:\n{data}",
        kind="fields",
        fields=(
            "FirstName",
            "LastName",
            "DateOfBirth",
            "DateOfExpiration",
            "Sex",
        ),
    ),
]
PROFILES = {profile.model_id: profile for profile in _PROFILE_LIST}


def get_profile(model_id: str) -> Profile:
    """Return the profile for a supported model."""
    try:
        return PROFILES[model_id]
    except KeyError as error:
        raise ValueError(f"Unsupported model: {model_id}") from error
