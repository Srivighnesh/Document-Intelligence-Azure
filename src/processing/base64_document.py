"""Base64 document content validation and conversion."""

import base64
import binascii
import re

DEFAULT_MAX_BYTES = 10 * 1024 * 1024
BASE64_CHARS_PER_BLOCK = 4
BASE64_BYTES_PER_BLOCK = 3
BASE64_MAX_LENGTH_PADDING = BASE64_CHARS_PER_BLOCK


class InvalidBase64Error(ValueError):
    """Base64 content is malformed."""


class EmptyDocumentError(ValueError):
    """Decoded document content is empty."""


class DocumentTooLargeError(ValueError):
    """Document content exceeds the configured size limit."""


class Base64Document:
    """Validate, decode, and encode Base64 document content."""

    def __init__(self, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        """Set the maximum decoded document size."""
        if max_bytes < 0:
            raise ValueError("max_bytes must not be negative.")
        self.max_bytes = max_bytes

    def decode(self, value: str) -> bytes:
        """Decode Base64 text into bytes."""
        if value.startswith("data:") and ";base64," in value:
            value = value.split(",", 1)[1]
        cleaned = re.sub(r"\s+", "", value)
        max_encoded_length = (
            self.max_bytes * BASE64_CHARS_PER_BLOCK // BASE64_BYTES_PER_BLOCK
            + BASE64_MAX_LENGTH_PADDING
        )
        if len(cleaned) > max_encoded_length:
            raise DocumentTooLargeError("Document exceeds the configured size limit.")
        try:
            content = base64.b64decode(cleaned, validate=True)
        except (binascii.Error, ValueError) as error:
            raise InvalidBase64Error("Base64 content is malformed.") from error
        if not content:
            raise EmptyDocumentError("Decoded document content is empty.")
        if len(content) > self.max_bytes:
            raise DocumentTooLargeError("Document exceeds the configured size limit.")
        return content

    def encode(self, content: bytes) -> str:
        """Encode bytes as a Base64 string."""
        return base64.b64encode(content).decode("ascii")
