import pytest

from src.processing.base64_document import (
    Base64Document,
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidBase64Error,
)


def test_decode_valid_base64() -> None:
    assert Base64Document().decode("aGVsbG8=") == b"hello"


def test_decode_data_url_prefix() -> None:
    assert Base64Document().decode("data:application/pdf;base64,aGVsbG8=") == b"hello"


def test_decode_ignores_whitespace() -> None:
    assert Base64Document().decode("aGVs\n bG8=\t") == b"hello"


def test_decode_rejects_invalid_base64() -> None:
    with pytest.raises(InvalidBase64Error):
        Base64Document().decode("not base64!")


def test_decode_rejects_empty_content() -> None:
    with pytest.raises(EmptyDocumentError):
        Base64Document().decode("")


def test_decode_rejects_oversized_content() -> None:
    with pytest.raises(DocumentTooLargeError):
        Base64Document(max_bytes=3).decode("YWJjZA==")


def test_encode_decode_round_trip() -> None:
    document = Base64Document()
    content = b"document bytes"

    assert document.decode(document.encode(content)) == content
