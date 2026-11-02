from src.services.foundry.response import parse_response


def test_parse_response_plain_json() -> None:
    assert parse_response('{"status": "ok"}') == {"status": "ok"}


def test_parse_response_fenced_json() -> None:
    assert parse_response('```json\n{"status": "ok"}\n```') == {"status": "ok"}


def test_parse_response_returns_non_json_unchanged() -> None:
    text = "not JSON"

    assert parse_response(text) == text
