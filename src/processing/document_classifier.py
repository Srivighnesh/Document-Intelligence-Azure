"""Content-based routing for the supported prebuilt document models."""





from __future__ import annotations


CLASSIFIER_VERSION = 2
FALLBACK_MODEL_ID = "prebuilt-layout"

_SIGNALS: dict[str, tuple[tuple[str, int], ...]] = {
    "prebuilt-invoice": (
        ("invoice", 3),
        ("invoice number", 3),
        ("invoice date", 2),
        ("bill to", 2),
        ("amount due", 2),
        ("purchase order", 2),
    ),
    "prebuilt-receipt": (
        ("receipt", 3),
        ("merchant", 2),
        ("transaction date", 2),
        ("change due", 2),
        ("cash tendered", 2),
    ),
    "prebuilt-idDocument": (
        ("aadhaar", 3),
        ("aadhar", 3),
        ("uidai", 3),
        ("unique identification authority of india", 3),
        ("aadhaar no", 3),
        ("aadhar no", 3),
        ("enrolment no", 2),
        ("enrollment no", 2),
        ("permanent account number", 3),
        ("pan card", 3),
        ("voter id", 3),
        ("elector photo identity card", 3),
        ("passport", 3),
        ("driver license", 3),
        ("driving license", 3),
        ("driving licence", 3),
        ("driver's license", 3),
        ("identity card", 3),
        ("identification card", 3),
        ("national id", 3),
        ("national identity", 3),
        ("social security", 3),
        ("residence permit", 3),
        ("date of birth", 2),
        ("government of india", 1),
        ("vid", 1),
        ("document number", 2),
        ("identification number", 2),
        ("date of expiration", 2),
        ("nationality", 2),
    ),
    "prebuilt-layout": (
        ("form 10-q", 3),
        ("commission file number", 3),
        ("quarterly period ended", 2),
        ("trading symbol", 2),
    ),
}


def classify_document(lines: list[str]) -> str:
    """Choose a supported model from OCR text, independent of file naming."""

    text = "\n".join(lines).casefold()
    scores = {
        model_id: sum(weight for signal, weight in signals if signal in text)
        for model_id, signals in _SIGNALS.items()
    }
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] < 2:
        return FALLBACK_MODEL_ID
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return FALLBACK_MODEL_ID
    return ranked[0][0]
