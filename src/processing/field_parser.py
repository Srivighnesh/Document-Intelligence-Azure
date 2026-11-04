"""Parse 10-Q cover-page fields from OCR lines."""

import re

from src.processing.field_values import field_result
from src.processing.profiles import Profile


FIELD_LABELS = {
    "VendorName": ("vendor name", "vendor", "supplier name", "supplier"),
    "CustomerName": ("customer name", "customer", "bill to"),
    "InvoiceId": ("invoice id", "invoice number", "invoice #", "invoice no"),
    "InvoiceDate": ("invoice date", "date of invoice"),
    "DueDate": ("due date", "payment due"),
    "InvoiceTotal": ("invoice total", "total amount"),
    "SubTotal": ("subtotal", "sub total"),
    "TotalTax": ("total tax", "tax"),
    "AmountDue": ("amount due", "balance due"),
    "MerchantName": ("merchant name", "merchant", "store name"),
    "TransactionDate": ("transaction date", "date of transaction"),
    "Total": ("total", "grand total"),
    "FirstName": ("first name", "given name"),
    "LastName": ("last name", "surname", "family name"),
    "DateOfBirth": ("date of birth", "birth date", "dob"),
    "CardNumber": (
        "card number",
        "document number",
        "id number",
        "license number",
        "driver license number",
        "passport number",
        "credit card number",
        "debit card number",
    ),
    "Address": ("address", "residential address", "permanent address"),
    "DateOfExpiration": ("date of expiration", "expiration date", "expiry date"),
    "Sex": ("sex", "gender"),
}
MIN_UPPERCASE_RATIO = 0.8


class ProfileFieldParser:
    """Derive profile fields from OCR labels when model fields are absent."""

    _ten_q_models = {"prebuilt-layout", "microsoft-10q-v1"}

    def parse(
        self, lines: list[str], profile: Profile
    ) -> dict[str, dict[str, object | None]]:
        """Parse configured profile fields from OCR lines."""
        if profile.model_id in self._ten_q_models:
            return TenQFieldParser().parse(lines, profile)
        parsed = self._parse_labeled_fields(lines, profile.fields)
        return {
            name: parsed.get(name, field_result(None))
            for name in profile.fields
        }

    def _parse_labeled_fields(
        self, lines: list[str], field_names: tuple[str, ...]
    ) -> dict[str, dict[str, object | None]]:
        parsed: dict[str, dict[str, object | None]] = {}
        for name in field_names:
            aliases = FIELD_LABELS.get(name, (self._humanize(name),))
            value = (
                self._find_address_value(lines)
                if name == "Address"
                else self._find_labeled_value(lines, aliases)
            )
            parsed[name] = field_result(value, value)
        return parsed

    def _find_address_value(self, lines: list[str]) -> str | None:
        """Collect an address label and its following OCR lines."""
        label = re.compile(
            r"^(?:address|residential address|permanent address)\s*[:#-]?\s*(.*)$",
            re.I,
        )
        stop = re.compile(
            r"^(?:qr code|aadhaar|aadhar|vid\b|date of birth|dob\b|"
            r"date of expiration|passport|document number|sex\b|gender\b|"
            r"nationality\b|name\b)",
            re.I,
        )
        for index, line in enumerate(lines):
            match = label.match(line.strip())
            if not match:
                continue
            parts = [match.group(1).strip()] if match.group(1).strip() else []
            for next_line in lines[index + 1 :]:
                candidate = next_line.strip()
                if not candidate or stop.match(candidate):
                    break
                parts.append(candidate)
                if len(parts) >= 5:
                    break
            return " ".join(parts) or None
        return None

    def _find_labeled_value(
        self, lines: list[str], aliases: tuple[str, ...]
    ) -> str | None:
        label_pattern = re.compile(
            rf"^(?:{'|'.join(re.escape(alias) for alias in aliases)})\s*[:#-]?\s*(.*)$",
            re.I,
        )
        for index, line in enumerate(lines):
            match = label_pattern.match(line.strip())
            if not match:
                continue
            value = match.group(1).strip(" :#-\t")
            if value:
                return value
            for next_line in lines[index + 1 :]:
                value = next_line.strip()
                if value:
                    return value
        return None

    def _humanize(self, name: str) -> str:
        """Convert a camel-case field name to a readable label."""
        return re.sub(r"(?<!^)([A-Z])", r" \1", name).lower()

class TenQFieldParser:
    """Derive 10-Q cover-page fields from OCR lines."""

    _commission = re.compile(r"Commission File Number\s*([\d-]+)?", re.I)
    _period = re.compile(r"Quarterly Period Ended\s+(.+)$", re.I)
    _company = re.compile(r"\b(CORPORATION|INC|LTD|CORP|COMPANY|LLC)\b", re.I)
    _incorporation = re.compile(
        r"\(STATE OF INCORPORATION\)|\(State or other jurisdiction", re.I
    )
    _zip = re.compile(r"\b\d{5}(-\d{4})?\b")
    _telephone = re.compile(r"\(?\d{3}\)?[\s-]\d{3}-\d{4}")
    _ticker = re.compile(r"\b[A-Z]{1,5}\b")
    _exchange = re.compile(
        r"THE NASDAQ STOCK MARKET LLC|NEW YORK STOCK EXCHANGE|NASDAQ|NYSE", re.I
    )

    def parse(
        self, lines: list[str], profile: Profile
    ) -> dict[str, dict[str, object | None]]:
        """Parse configured 10-Q profile fields from OCR lines."""
        commission, commission_index = self._commission_number(lines)
        values = {
            "companyName": self._company_name(lines, commission_index),
            "commissionFileNumber": commission,
            "reportingPeriodEndDate": self._reporting_period(lines),
            "incorporationState": self._incorporation_state(lines),
            "companyAddress": self._company_address(lines),
            "telephoneNumber": self._telephone_number(lines),
            "tickerSymbols": self._ticker_symbols(lines),
            "exchangeNames": self._exchange_names(lines),
        }
        return {
            name: self._field_result(values.get(name))
            for name in profile.fields
        }

    def _commission_number(self, lines: list[str]) -> tuple[str | None, int]:
        for index, line in enumerate(lines):
            match = self._commission.search(line)
            if match:
                if match.group(1):
                    return match.group(1), index
                if index + 1 < len(lines):
                    number = re.search(r"[\d-]+", lines[index + 1])
                    if number:
                        return number.group(), index + 1
        return None, -1

    def _company_name(self, lines: list[str], commission_index: int) -> str | None:
        if commission_index < 0 or commission_index + 1 >= len(lines):
            return None
        line = lines[commission_index + 1].strip()
        letters = [char for char in line if char.isalpha()]
        uppercase_count = sum(char.isupper() for char in letters)
        if letters and uppercase_count / len(letters) >= MIN_UPPERCASE_RATIO:
            if self._company.search(line):
                return line
        return None

    def _reporting_period(self, lines: list[str]) -> str | None:
        for line in lines:
            match = self._period.search(line)
            if match:
                return match.group(1).strip().rstrip(" .,:;")
        return None

    def _incorporation_state(self, lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if self._incorporation.search(line) and index:
                return lines[index - 1].strip() or None
        return None

    def _company_address(self, lines: list[str]) -> str | None:
        for index, line in enumerate(lines):
            if self._incorporation.search(line):
                for address in lines[index + 1 :]:
                    if self._zip.search(address):
                        return address.strip()
        return None

    def _telephone_number(self, lines: list[str]) -> str | None:
        for line in lines:
            match = self._telephone.search(line)
            if match:
                return match.group()
        return None

    def _ticker_symbols(self, lines: list[str]) -> list[str] | None:
        indexes = [
            index for index, line in enumerate(lines)
            if "trading symbol" in line.lower() or "common stock" in line.lower()
        ]
        symbols: list[str] = []
        for index in indexes:
            for line in lines[index + 1 :]:
                stripped = line.strip()
                if stripped and self._ticker.fullmatch(stripped):
                    if stripped not in symbols:
                        symbols.append(stripped)
                    break
        return symbols or None

    def _exchange_names(self, lines: list[str]) -> list[str] | None:
        known = {
            "NASDAQ": "NASDAQ",
            "NYSE": "NYSE",
            "NEW YORK STOCK EXCHANGE": "NEW YORK STOCK EXCHANGE",
            "THE NASDAQ STOCK MARKET LLC": "THE NASDAQ STOCK MARKET LLC",
        }
        found: list[str] = []
        for line in lines:
            for match in self._exchange.finditer(line):
                name = known[match.group().upper()]
                if name not in found:
                    found.append(name)
        return found or None

    def _field_result(self, value: object | None) -> dict[str, object | None]:
        """Shape one parsed value consistently."""
        content = ", ".join(value) if isinstance(value, list) else value
        return field_result(value, content)
